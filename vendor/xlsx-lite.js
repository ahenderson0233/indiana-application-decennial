/* xlsx-lite - read and write .xlsx with no dependencies and no CDN.
   =============================================================================================
   G74. Operator, 2026-08-19: "ANY Excel sheet should be able to be inputted and saved to the
   application ... The Excel outputs should also be nearly all-encompassing."

   WHY THIS EXISTS RATHER THAN SheetJS. This site is static, offline-capable and vendored by
   policy - `vendor/maplibre-gl.css` is already here for the same reason. SheetJS is ~900 KB to
   solve a problem that is, for our two directions, a ZIP container and two XML shapes. An .xlsx
   is a ZIP of XML parts; the browser already ships the inflater we need
   (DecompressionStream('deflate-raw')). So this is ~9 KB and has no supply chain.

   WHAT IT DOES
     XLSXLite.read(arrayBuffer)  -> { sheets: [ { name, rows: [ [cell, ...], ... ] } ] }
     XLSXLite.write(sheets)      -> Blob            sheets = [ { name, rows: [[...]] } ]
     XLSXLite.readAny(file)      -> { sheets }      .xlsx | .xlsm | .csv | .tsv | .txt

   WHAT IT DELIBERATELY DOES NOT DO, stated rather than discovered by a user later:
     * FORMULAS are read as their CACHED VALUE, which is what Excel stored last time it saved.
       A workbook saved by a tool that writes no cached value reads those cells empty. We do not
       evaluate formulas.
     * DATES come back as Excel SERIAL NUMBERS (45000-ish), not Date objects, unless the cell was
       stored as text. Distinguishing a date from a number needs the style table and the number
       format, and guessing is worse than being explicit: `XLSXLite.excelDate(n)` is provided so
       the CALLER decides, per column, whether a number is a date.
     * Merged cells report their value in the top-left cell only, which is where the file puts it.
     * .xls (the pre-2007 binary) is NOT a ZIP and is NOT supported. It is reported as such
       instead of failing with a confusing ZIP error.
     * The writer emits inline strings and no styling. Numbers stay numbers so Excel can sum them;
       everything else is text. No column widths, no colour - this is data interchange.

   Nothing here touches the network. A file the user picks is read in the browser and never
   uploaded; the site has no server to upload it to.
   ============================================================================================= */
(function (global) {
  "use strict";

  /* ---------- ZIP: central-directory reader -------------------------------------------------
     We read the CENTRAL DIRECTORY rather than walking local headers, because a local header may
     carry sizes of 0 with the real values in a trailing data descriptor (bit 3 of the flags).
     Excel does not usually do that, but plenty of writers that produce .xlsx do, and a reader
     that walks local headers silently truncates those files. */
  const dv = (b) => new DataView(b);
  const u8 = (b) => new Uint8Array(b);

  function findEOCD(buf) {
    const v = dv(buf), n = buf.byteLength;
    // comment can be up to 65535 bytes, so scan back at most that far plus the 22-byte record
    const lo = Math.max(0, n - 65557);
    for (let i = n - 22; i >= lo; i--) if (v.getUint32(i, true) === 0x06054b50) return i;
    return -1;
  }

  function entries(buf) {
    const v = dv(buf), eocd = findEOCD(buf);
    if (eocd < 0) throw new Error("not a ZIP archive (no end-of-central-directory record)");
    let count = v.getUint16(eocd + 10, true);
    let off = v.getUint32(eocd + 16, true);
    // ZIP64: 0xFFFF/0xFFFFFFFF are sentinels meaning "look in the ZIP64 record".
    if (count === 0xffff || off === 0xffffffff) {
      const loc = eocd - 20;
      if (loc >= 0 && v.getUint32(loc, true) === 0x07064b50) {
        const z64 = Number(v.getBigUint64(loc + 8, true));
        if (v.getUint32(z64, true) === 0x06064b50) {
          count = Number(v.getBigUint64(z64 + 32, true));
          off = Number(v.getBigUint64(z64 + 48, true));
        }
      }
    }
    const out = new Map();
    for (let i = 0; i < count && off + 46 <= buf.byteLength; i++) {
      if (v.getUint32(off, true) !== 0x02014b50) break;
      const method = v.getUint16(off + 10, true);
      const csize = v.getUint32(off + 20, true);
      const nlen = v.getUint16(off + 28, true);
      const elen = v.getUint16(off + 30, true);
      const clen = v.getUint16(off + 32, true);
      const lho = v.getUint32(off + 42, true);
      const name = new TextDecoder().decode(u8(buf).subarray(off + 46, off + 46 + nlen));
      out.set(name, { method, csize, lho });
      off += 46 + nlen + elen + clen;
    }
    return out;
  }

  async function readEntry(buf, e) {
    const v = dv(buf);
    if (v.getUint32(e.lho, true) !== 0x04034b50) throw new Error("bad local file header");
    const nlen = v.getUint16(e.lho + 26, true);
    const elen = v.getUint16(e.lho + 28, true);
    const start = e.lho + 30 + nlen + elen;
    const raw = u8(buf).subarray(start, start + e.csize);
    if (e.method === 0) return new TextDecoder().decode(raw);
    if (e.method !== 8) throw new Error("unsupported ZIP compression method " + e.method);
    const ds = new DecompressionStream("deflate-raw");
    const stream = new Blob([raw]).stream().pipeThrough(ds);
    return await new Response(stream).text();
  }

  /* ---------- tiny XML helpers ---------------------------------------------------------------
     DOMParser is in every browser we support and is far safer than regex over XML - an attribute
     containing ">" is legal and would defeat a regex. */
  const parseXml = (s) => new DOMParser().parseFromString(s, "application/xml");
  const allTags = (doc, local) =>
    Array.from(doc.getElementsByTagName("*")).filter((n) => n.localName === local);

  // "BC" -> 54 (0-based). Column letters are base-26 with no zero.
  function colIndex(ref) {
    let n = 0;
    for (let i = 0; i < ref.length; i++) {
      const c = ref.charCodeAt(i);
      if (c < 65 || c > 90) break;
      n = n * 26 + (c - 64);
    }
    return n - 1;
  }

  /* ---------- READ ---------------------------------------------------------------------------- */
  async function read(buf) {
    if (buf.byteLength >= 8) {
      const sig = u8(buf).subarray(0, 8);
      // D0 CF 11 E0 A1 B1 1A E1 = the OLE compound-file magic used by the pre-2007 .xls format
      if (sig[0] === 0xd0 && sig[1] === 0xcf && sig[2] === 0x11 && sig[3] === 0xe0)
        throw new Error("this is a legacy .xls file, not .xlsx. Re-save it as .xlsx or .csv");
    }
    const zip = entries(buf);
    const get = async (name) => (zip.has(name) ? readEntry(buf, zip.get(name)) : null);

    // shared strings: cells with t="s" hold an INDEX into this table, not the text
    const shared = [];
    const ssXml = await get("xl/sharedStrings.xml");
    if (ssXml) {
      for (const si of allTags(parseXml(ssXml), "si")) {
        // rich text splits one string across many <t> runs; concatenate, and drop <rPh> phonetics
        let s = "";
        for (const t of Array.from(si.getElementsByTagName("*")))
          if (t.localName === "t" && !(t.parentNode && t.parentNode.localName === "rPh"))
            s += t.textContent;
        shared.push(s);
      }
    }

    // sheet name -> part path, via the workbook and its relationships
    const relXml = await get("xl/_rels/workbook.xml.rels");
    const rels = new Map();
    if (relXml)
      for (const r of allTags(parseXml(relXml), "Relationship"))
        rels.set(r.getAttribute("Id"), r.getAttribute("Target").replace(/^\/?xl\//, "").replace(/^\//, ""));

    const wbXml = await get("xl/workbook.xml");
    const wanted = [];
    if (wbXml) {
      for (const sh of allTags(parseXml(wbXml), "sheet")) {
        const rid = sh.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id")
                 || sh.getAttribute("r:id");
        const target = rels.get(rid);
        wanted.push({ name: sh.getAttribute("name") || "Sheet", path: target ? "xl/" + target : null });
      }
    }
    // a workbook part we could not follow still has sheets on disk - fall back to what is there
    if (!wanted.length)
      for (const k of zip.keys())
        if (/^xl\/worksheets\/sheet\d+\.xml$/.test(k)) wanted.push({ name: k.split("/").pop(), path: k });

    const sheets = [];
    for (const w of wanted) {
      if (!w.path || !zip.has(w.path)) continue;
      const doc = parseXml(await readEntry(buf, zip.get(w.path)));
      const rows = [];
      for (const row of allTags(doc, "row")) {
        const cells = [];
        for (const c of Array.from(row.children)) {
          if (c.localName !== "c") continue;
          const ref = c.getAttribute("r") || "";
          const at = colIndex(ref);
          const t = c.getAttribute("t");
          let val = null;
          if (t === "inlineStr") {
            val = Array.from(c.getElementsByTagName("*"))
              .filter((n) => n.localName === "t").map((n) => n.textContent).join("");
          } else {
            const vEl = Array.from(c.children).find((n) => n.localName === "v");
            const raw = vEl ? vEl.textContent : null;
            if (raw === null || raw === "") val = null;
            else if (t === "s") val = shared[Number(raw)] ?? "";
            else if (t === "b") val = raw === "1";
            else if (t === "e") val = raw;                 // an Excel error such as #N/A
            else if (t === "str") val = raw;               // cached formula result, already text
            else { const n = Number(raw); val = Number.isFinite(n) ? n : raw; }
          }
          if (at >= 0) { while (cells.length < at) cells.push(null); cells[at] = val; }
          else cells.push(val);
        }
        const idx = Number(row.getAttribute("r"));
        if (Number.isFinite(idx) && idx > 0) { while (rows.length < idx - 1) rows.push([]); rows[idx - 1] = cells; }
        else rows.push(cells);
      }
      sheets.push({ name: w.name, rows });
    }
    if (!sheets.length) throw new Error("no worksheets found in this workbook");
    return { sheets };
  }

  /* ---------- delimited text ------------------------------------------------------------------
     RFC 4180 quoting, and the delimiter is SNIFFED rather than assumed: a European export is
     semicolon-separated and a tab file is common out of database tools. Guessing "," on those
     yields one giant column, which reads to the user as "your file is broken". */
  function sniff(text) {
    const line = (text.split(/\r?\n/).find((l) => l.trim()) || "");
    let best = ",", bestN = -1;
    for (const d of [",", ";", "\t", "|"]) {
      let n = 0, inQ = false;
      for (const ch of line) { if (ch === '"') inQ = !inQ; else if (ch === d && !inQ) n++; }
      if (n > bestN) { bestN = n; best = d; }
    }
    return best;
  }

  function parseDelimited(text, delim) {
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);      // strip a UTF-8 BOM
    const d = delim || sniff(text);
    const rows = []; let row = [""], inQ = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (inQ) {
        if (ch === '"') { if (text[i + 1] === '"') { row[row.length - 1] += '"'; i++; } else inQ = false; }
        else row[row.length - 1] += ch;
      } else if (ch === '"') inQ = true;
      else if (ch === d) row.push("");
      else if (ch === "\n") { rows.push(row); row = [""]; }
      else if (ch === "\r") { /* handled by the \n */ }
      else row[row.length - 1] += ch;
    }
    if (row.length > 1 || row[0] !== "") rows.push(row);
    // numeric-looking cells become numbers so the same downstream code works for xlsx and csv
    return rows.map((r) => r.map((c) => {
      const s = String(c).trim();
      if (s === "") return null;
      const n = Number(s.replace(/,(?=\d{3}\b)/g, ""));
      return s !== "" && Number.isFinite(n) && /^[-+]?[\d.,]+(e[-+]?\d+)?$/i.test(s) ? n : c;
    }));
  }

  async function readAny(file) {
    const name = (file.name || "").toLowerCase();
    if (/\.(csv|tsv|txt)$/.test(name)) {
      const text = await file.text();
      return { sheets: [{ name: file.name, rows: parseDelimited(text) }] };
    }
    return read(await file.arrayBuffer());
  }

  /* ---------- WRITE ---------------------------------------------------------------------------
     STORED entries (method 0) rather than deflate: it costs size on disk and buys correctness -
     CompressionStream is not universal and a wrong CRC produces a file Excel refuses to open with
     no useful message. Interchange files are opened once; the bytes are cheap. */
  let CRC = null;
  function crc32(bytes) {
    if (!CRC) {
      CRC = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        CRC[n] = c >>> 0;
      }
    }
    let c = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) c = CRC[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }

  const xmlEsc = (s) => String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    // XML 1.0 forbids most control characters outright. Excel writes them as nothing; a raw
    // 0x07 in a cell makes the whole workbook unopenable, which is a very confusing failure.
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, "");

  function colName(i) {
    let s = "";
    for (i += 1; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s;
    return s;
  }

  function sheetXml(rows) {
    const out = [`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
      `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>`];
    rows.forEach((row, r) => {
      out.push(`<row r="${r + 1}">`);
      (row || []).forEach((v, c) => {
        if (v === null || v === undefined || v === "") return;
        const ref = colName(c) + (r + 1);
        if (typeof v === "number" && Number.isFinite(v)) out.push(`<c r="${ref}"><v>${v}</v></c>`);
        else if (typeof v === "boolean") out.push(`<c r="${ref}" t="b"><v>${v ? 1 : 0}</v></c>`);
        else out.push(`<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xmlEsc(v)}</t></is></c>`);
      });
      out.push(`</row>`);
    });
    out.push(`</sheetData></worksheet>`);
    return out.join("");
  }

  function write(sheets) {
    const enc = new TextEncoder();
    // Excel refuses duplicate or over-long sheet names, and : \ / ? * [ ] are illegal in them.
    const seen = new Set();
    const safe = sheets.map((s, i) => {
      let n = String(s.name || `Sheet${i + 1}`).replace(/[:\\/?*[\]]/g, "-").slice(0, 31) || `Sheet${i + 1}`;
      let base = n, k = 2;
      while (seen.has(n.toLowerCase())) n = (base.slice(0, 28) + "_" + k++).slice(0, 31);
      seen.add(n.toLowerCase());
      return { name: n, rows: s.rows || [] };
    });

    const parts = [];
    parts.push(["[Content_Types].xml",
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
      safe.map((s, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("") +
      `</Types>`]);
    parts.push(["_rels/.rels",
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
      `</Relationships>`]);
    parts.push(["xl/workbook.xml",
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ` +
      `xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>` +
      safe.map((s, i) => `<sheet name="${xmlEsc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("") +
      `</sheets></workbook>`]);
    parts.push(["xl/_rels/workbook.xml.rels",
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      safe.map((s, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join("") +
      `</Relationships>`]);
    safe.forEach((s, i) => parts.push([`xl/worksheets/sheet${i + 1}.xml`, sheetXml(s.rows)]));

    const chunks = [], central = [];
    let offset = 0;
    for (const [name, text] of parts) {
      const nameB = enc.encode(name), data = enc.encode(text);
      const crc = crc32(data);
      const lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0, true);
      lh.setUint16(8, 0, true);                       // method 0 = stored
      lh.setUint16(10, 0, true); lh.setUint16(12, 0x2100, true);   // a fixed 2000-01-01 timestamp
      lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
      lh.setUint16(26, nameB.length, true); lh.setUint16(28, 0, true);
      chunks.push(new Uint8Array(lh.buffer), nameB, data);

      const cd = new DataView(new ArrayBuffer(46));
      cd.setUint32(0, 0x02014b50, true); cd.setUint16(4, 20, true); cd.setUint16(6, 20, true);
      cd.setUint16(8, 0, true); cd.setUint16(10, 0, true);
      cd.setUint16(12, 0, true); cd.setUint16(14, 0x2100, true);
      cd.setUint32(16, crc, true); cd.setUint32(20, data.length, true); cd.setUint32(24, data.length, true);
      cd.setUint16(28, nameB.length, true); cd.setUint32(42, offset, true);
      central.push(new Uint8Array(cd.buffer), nameB);
      offset += 30 + nameB.length + data.length;
    }
    const cdSize = central.reduce((n, c) => n + c.length, 0);
    const eo = new DataView(new ArrayBuffer(22));
    eo.setUint32(0, 0x06054b50, true);
    eo.setUint16(8, parts.length, true); eo.setUint16(10, parts.length, true);
    eo.setUint32(12, cdSize, true); eo.setUint32(16, offset, true);
    return new Blob([...chunks, ...central, new Uint8Array(eo.buffer)],
      { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }

  /* Excel's serial-date epoch is 1899-12-30, NOT 1900-01-01 - the format deliberately reproduces
     a 1900 leap-year bug from Lotus 1-2-3, so serial 60 is a day that never existed. Offsetting
     from the 30th absorbs it for every real date after 1900-03-01. */
  const excelDate = (n) => (Number.isFinite(n) ? new Date(Math.round((n - 25569) * 86400000)) : null);

  function download(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  global.XLSXLite = { read, readAny, write, parseDelimited, sniff, excelDate, download, colName };
})(window);
