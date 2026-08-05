#!/usr/bin/env node

const [portRaw, exactText] = process.argv.slice(2);
const port = Number(portRaw);

function stop(message, status = 64) {
  process.stderr.write(`${message}\n`);
  process.exit(status);
}

if (!Number.isInteger(port) || port < 1024 || port > 65535) {
  stop("invalid local debugging port");
}
if (
  typeof exactText !== "string" ||
  exactText.length < 1 ||
  exactText.length > 100 ||
  /[\u0000-\u001f\u007f]/u.test(exactText)
) {
  stop("exact web text must be 1-100 printable characters");
}

let targets;
try {
  const response = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!response.ok) throw new Error("target list unavailable");
  targets = await response.json();
} catch {
  stop("Chrome debugging target list is unavailable", 69);
}

const pages = targets.filter((target) => {
  if (target.type !== "page" || typeof target.url !== "string") return false;
  try {
    const url = new URL(target.url);
    return url.protocol === "https:" && [
      "aula.dk",
      "www.aula.dk",
      "broker.unilogin.dk",
      "login-idp.ishoj.dk",
    ].includes(url.hostname);
  } catch {
    return false;
  }
});

if (pages.length === 0) {
  process.stdout.write(JSON.stringify({ ok: false, stage: "page", page_count: pages.length }));
  process.exit(2);
}

function buildExpression(click) {
  return `(() => {
  const wanted = ${JSON.stringify(exactText)};
  const normalize = (value) => value.replace(/\\s+/gu, " ").trim();
  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      rect.width > 0 && rect.height > 0 && !element.disabled &&
      element.getAttribute("aria-disabled") !== "true";
  };
  const clickableSelector = "button, a, [role='button'], [tabindex='0']";
  const exactLabels = [...document.querySelectorAll("body *")].filter((element) =>
    visible(element) && normalize(element.textContent || "") === wanted &&
    ![...element.children].some((child) =>
      visible(child) && normalize(child.textContent || "") === wanted
    )
  );
  const matches = [...new Set(exactLabels.map((label) =>
    label.matches(clickableSelector) ? label : label.closest(clickableSelector)
  ).filter((element) => element && visible(element)))];
  if (${JSON.stringify(click)} && matches.length === 1) matches[0].click();
  return { count: matches.length, clicked: ${JSON.stringify(click)} && matches.length === 1 };
})()`;
}

async function evaluate(target, expression) {
  const endpoint = new URL(target.webSocketDebuggerUrl);
  endpoint.hostname = "127.0.0.1";
  endpoint.port = String(port);
  const socket = new WebSocket(endpoint);
  try {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("open timeout")), 5000);
      socket.addEventListener("open", () => {
        clearTimeout(timeout);
        resolve();
      }, { once: true });
      socket.addEventListener("error", () => reject(new Error("open failed")), { once: true });
    });
    socket.send(JSON.stringify({
      id: 1,
      method: "Runtime.evaluate",
      params: { expression, returnByValue: true, awaitPromise: true, userGesture: true },
    }));
    const response = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("response timeout")), 5000);
      socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        if (message.id !== 1) return;
        clearTimeout(timeout);
        resolve(message);
      });
      socket.addEventListener("error", () => reject(new Error("response failed")), { once: true });
    });
    const value = response?.result?.result?.value;
    if (!value || typeof value.count !== "number") throw new Error("invalid result");
    return value;
  } finally {
    socket.close();
  }
}

let counts;
try {
  counts = await Promise.all(pages.map((page) => evaluate(page, buildExpression(false))));
} catch {
  stop("Chrome semantic web action failed", 69);
}
const count = counts.reduce((total, value) => total + value.count, 0);
if (count !== 1) {
  process.stdout.write(JSON.stringify({ ok: false, stage: "control", count }));
  process.exit(count === 0 ? 2 : 3);
}
const pageIndex = counts.findIndex((value) => value.count === 1);
let clicked;
try {
  clicked = await evaluate(pages[pageIndex], buildExpression(true));
} catch {
  stop("Chrome semantic web action failed", 69);
}
if (!clicked.clicked || clicked.count !== 1) {
  stop("Chrome semantic web action changed before click", 69);
}
process.stdout.write(JSON.stringify({ ok: true, stage: "control", count: 1 }));
