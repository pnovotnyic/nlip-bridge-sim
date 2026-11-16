// Driver for the TypeScript example client (nlip_client_pwa_ts/src/components/network.ts), run with node.
// fetch is replaced by a stub; the real client code builds the request and reads the response.
// One JSON request per line on stdin, one reply per line.
//   ops: build {kind: text|image|control_upload} | receive {kind: text|upload, obj}
//        | send {kind, target}  (really send to target, a base URL that replaces the client's hard-coded server)
import readline from "node:readline";
import path from "node:path";
import { pathToFileURL } from "node:url";

const src = path.resolve(process.argv[2]);
const net = await import(pathToFileURL(src).href);
const log = console.log;
console.log = () => {}; // the client logs a lot

const realFetch = globalThis.fetch;
let stub = null;
let sent = [];
let target = null;
globalThis.fetch = async (url, init) => {
  sent.push({ url: String(url), method: init?.method, headers: init?.headers, body: init?.body ? JSON.parse(init.body) : null });
  if (target) {
    const u = String(url).replace("https://druid.eecs.umich.edu", target);
    const r = await realFetch(u, init);
    const text = await r.text();
    sent[sent.length - 1].status = r.status;
    sent[sent.length - 1].response = text;
    return new Response(text, { status: r.status, headers: r.headers });
  }
  return new Response(JSON.stringify(stub), { status: 200, headers: { "content-type": "application/json" } });
};
async function run(kind, arg) {
  if (kind === "text") return net.sendTextMessage(arg ?? "hello", false);
  if (kind === "image") return net.sendImageMessage("what is this", "AAEC", "image/png", false);
  if (kind === "control_upload" || kind === "upload") return net.requestUploadUrl();
  throw new Error("kind " + kind);
}

const rl = readline.createInterface({ input: process.stdin });
for await (const line of rl) {
  const req = JSON.parse(line);
  sent = [];
  let out;
  try {
    if (req.op === "build") {
      stub = { format: "text", subformat: "english", content: "stub" };
      target = null;
      try { await run(req.kind === "control_upload" ? "upload" : req.kind); } catch (e) { /* the stub is not an upload url */ }
      out = { out: sent[0]?.body, url: sent[0]?.url, method: sent[0]?.method, headers: sent[0]?.headers };
    } else if (req.op === "receive") {
      stub = req.obj;
      target = null;
      try {
        const v = await run(req.kind);
        out = { accepted: true, value: v === undefined ? null : v };
      } catch (e) {
        out = { accepted: false, error: String(e.message || e) };
      }
    } else if (req.op === "send") {
      target = req.target;
      stub = null;
      try {
        const v = await run(req.kind, req.text);
        out = { accepted: true, value: v === undefined ? null : v, sent: sent[0]?.body, status: sent[0]?.status, response: sent[0]?.response };
      } catch (e) {
        out = { accepted: false, error: String(e.message || e), sent: sent[0]?.body, status: sent[0]?.status, response: sent[0]?.response };
      }
    } else out = { driver_error: "op " + req.op };
  } catch (e) {
    out = { driver_error: String(e.stack || e) };
  }
  log(JSON.stringify(out));
}
