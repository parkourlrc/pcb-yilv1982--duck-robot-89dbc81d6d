const fs = require("node:fs");
const path = require("node:path");
const sharp = require(process.argv[2]);
const evidence = path.resolve(process.argv[3]);
async function main() {
  for (const side of ["front", "back"]) {
    const source = path.join(evidence, "panel-r18-" + side + ".svg");
    await sharp(source, { density: 180 }).resize({ width: 1700 }).flatten({ background: "white" }).png().toFile(source.replace(".svg", ".png"));
  }
  const source = fs.readFileSync(path.join(evidence, "panel-r18-front.svg"), "utf8");
  const crop = source.replace(/width="[^"]+" height="[^"]+" viewBox="[^"]+"/, 'width="90mm" height="63mm" viewBox="13 38 10 7"');
  fs.writeFileSync(path.join(evidence, "panel-r18-mouse-bites.svg"), crop);
  await sharp(Buffer.from(crop), { density: 180 }).resize({ width: 1400 }).flatten({ background: "white" }).png().toFile(path.join(evidence, "panel-r18-mouse-bites.png"));
}
main().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
