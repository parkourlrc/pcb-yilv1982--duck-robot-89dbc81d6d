const sharp = require(process.argv[2]);
const path = require("node:path");
const directory = path.resolve(process.argv[3]);
const filename = process.argv[4] || "placement";
sharp(path.join(directory, filename + ".svg"), { density: 170 })
  .resize({ width: 1600 })
  .flatten({ background: "white" })
  .png()
  .toFile(path.join(directory, filename + ".png"))
  .then(() => process.stdout.write("Rendered " + filename + "\n"))
  .catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
