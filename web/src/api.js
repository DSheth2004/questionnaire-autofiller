async function check(res) {
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res;
}

export const getInfo = () => fetch("/api/info").then(check).then((r) => r.json());

export const ask = (question, mode) =>
  fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  }).then(check).then((r) => r.json());

/** Streams answered rows; calls onEvent for each {type: start|row|done} line. */
export async function fill(file, mode, onEvent, signal) {
  const form = new FormData();
  if (file) form.append("file", file);
  form.append("mode", mode);
  const res = await check(await fetch("/api/fill", { method: "POST", body: form, signal }));
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop();
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line));
  }
}

export async function exportXlsx(results) {
  const res = await check(
    await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results }),
    })
  );
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: "answers.xlsx" });
  a.click();
  URL.revokeObjectURL(url);
}
