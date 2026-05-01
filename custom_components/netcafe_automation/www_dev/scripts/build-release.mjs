import { promises as fs } from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { minify as terserMinify } from "terser";
import JavaScriptObfuscator from "javascript-obfuscator";
import CleanCSS from "clean-css";
import { minify as minifyHtml } from "html-minifier-terser";

const args = new Set(process.argv.slice(2));
const hashed = args.has("--hashed");

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(scriptDir, "..");
const projectDir = path.resolve(srcDir, "..");
const publicDir = path.join(projectDir, "www");
const releaseDir = path.join(projectDir, "www_release");
const stagingDir = path.join(projectDir, ".www_build_staging");
const manifestPath = path.join(stagingDir, "release-manifest.json");

const rootCopyFiles = [
  "__init__.py",
  "index.html",
  "index2.html",
  "1.html",
  "login.html",
  "subcontrol_app.html",
  "automation_config.html",
  "automation_refactor.css",
  "开灯.png",
  "关灯.png",
  "favicon.ico",
  "favicon.png",
];

function contentHash(input) {
  return crypto.createHash("sha256").update(input).digest("hex").slice(0, 8);
}

function makeOutputName(baseName, extension, content) {
  if (!hashed) {
    return `${baseName}${extension}`;
  }
  return `${baseName}.${contentHash(content)}${extension}`;
}

async function ensureCleanDir(targetDir) {
  await fs.mkdir(targetDir, { recursive: true });
  const entries = await fs.readdir(targetDir, { withFileTypes: true });
  for (const entry of entries) {
    await fs.rm(path.join(targetDir, entry.name), { recursive: true, force: true });
  }
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function copyFileIfPresent(relativePath) {
  const sourcePath = path.join(srcDir, relativePath);
  if (!(await exists(sourcePath))) {
    return;
  }
  const targetPath = path.join(stagingDir, relativePath);
  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  await fs.copyFile(sourcePath, targetPath);
}

async function copyDir(relativePath) {
  const sourcePath = path.join(srcDir, relativePath);
  if (!(await exists(sourcePath))) {
    return;
  }
  await fs.cp(sourcePath, path.join(stagingDir, relativePath), { recursive: true });
}

async function buildIconsManifest() {
  const iconsDir = path.join(srcDir, "icons");
  if (!(await exists(iconsDir))) {
    return;
  }
  const entries = await fs.readdir(iconsDir, { withFileTypes: true });
  const imageFiles = entries
    .filter((entry) => entry.isFile() && /\.(png|jpg|jpeg|gif|webp|svg|ico)$/i.test(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, "zh-CN"));

  await copyDir("icons");
  const manifest = {
    generatedAt: new Date().toISOString(),
    icons: imageFiles.map((fileName, index) => {
      const baseName = fileName.replace(/\.[^.]+$/, "");
      return {
        key: baseName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || `icon-${index + 1}`,
        label: baseName,
        note: fileName,
        file: fileName,
      };
    }),
  };
  const manifestTarget = path.join(stagingDir, "icons", "manifest.json");
  await fs.mkdir(path.dirname(manifestTarget), { recursive: true });
  await fs.writeFile(manifestTarget, JSON.stringify(manifest, null, 2), "utf8");
}

function updateHtmlAssetRefs(html, cssFileName, jsFileName) {
  return html
    .replaceAll("./1.css", `./${cssFileName}`)
    .replaceAll("./1.js", `./${jsFileName}`)
    .replaceAll('href="1.css"', `href="${cssFileName}"`)
    .replaceAll('src="1.js"', `src="${jsFileName}"`);
}

function updatePythonStaticMap(pyText, cssFileName, jsFileName) {
  return pyText
    .replace(
      /"1\.css": os\.path\.join\(_WWW_ROOT, "1\.css"\),/g,
      `"${cssFileName}": os.path.join(_WWW_ROOT, "${cssFileName}"),`
    )
    .replace(
      /"1\.js": os\.path\.join\(_WWW_ROOT, "1\.js"\),/g,
      `"${jsFileName}": os.path.join(_WWW_ROOT, "${jsFileName}"),`
    );
}

async function buildCss() {
  const source = await fs.readFile(path.join(srcDir, "1.css"), "utf8");
  const output = new CleanCSS({
    level: 2,
    sourceMap: false,
  }).minify(source);

  if (output.errors.length > 0) {
    throw new Error(`CSS minify failed: ${output.errors.join("; ")}`);
  }

  const cssText = output.styles;
  const fileName = makeOutputName("style", ".css", cssText);
  await fs.mkdir(stagingDir, { recursive: true });
  await fs.writeFile(path.join(stagingDir, hashed ? fileName : "1.css"), cssText, "utf8");
  return {
    fileName: hashed ? fileName : "1.css",
    bytes: Buffer.byteLength(cssText),
  };
}

async function buildJs() {
  const source = await fs.readFile(path.join(srcDir, "1.js"), "utf8");
  const minified = await terserMinify(source, {
    compress: {
      passes: 2,
      drop_console: false,
      drop_debugger: true,
    },
    mangle: true,
    format: {
      comments: false,
    },
    sourceMap: false,
    toplevel: false,
    keep_fnames: true,
  });

  if (!minified.code) {
    throw new Error("JS minify failed: empty output");
  }

  const obfuscated = JavaScriptObfuscator.obfuscate(minified.code, {
    compact: true,
    controlFlowFlattening: false,
    deadCodeInjection: false,
    disableConsoleOutput: false,
    identifierNamesGenerator: "hexadecimal",
    renameGlobals: false,
    rotateStringArray: true,
    selfDefending: false,
    splitStrings: false,
    stringArray: true,
    stringArrayEncoding: [],
    stringArrayThreshold: 0.75,
    transformObjectKeys: false,
    unicodeEscapeSequence: false,
  });

  const jsText = obfuscated.getObfuscatedCode();
  const fileName = makeOutputName("app", ".js", jsText);
  await fs.mkdir(stagingDir, { recursive: true });
  await fs.writeFile(path.join(stagingDir, hashed ? fileName : "1.js"), jsText, "utf8");
  return {
    fileName: hashed ? fileName : "1.js",
    bytes: Buffer.byteLength(jsText),
  };
}

async function buildHtmlFiles(cssFileName, jsFileName) {
  const htmlFiles = ["1.html"];

  for (const file of htmlFiles) {
    const sourcePath = path.join(srcDir, file);
    if (!(await exists(sourcePath))) {
      continue;
    }
    const source = await fs.readFile(sourcePath, "utf8");
    const updated = updateHtmlAssetRefs(source, cssFileName, jsFileName);
    const minified = await minifyHtml(updated, {
      collapseWhitespace: true,
      removeComments: true,
      removeRedundantAttributes: true,
      removeScriptTypeAttributes: true,
      removeStyleLinkTypeAttributes: true,
      keepClosingSlash: true,
      minifyCSS: false,
      minifyJS: false,
    });
    await fs.mkdir(stagingDir, { recursive: true });
    await fs.writeFile(path.join(stagingDir, file), minified, "utf8");
  }

  for (const passthrough of ["index.html", "index2.html", "login.html", "subcontrol_app.html", "automation_config.html"]) {
    const sourcePath = path.join(srcDir, passthrough);
    if (!(await exists(sourcePath))) {
      continue;
    }
    const source = await fs.readFile(sourcePath, "utf8");
    const updated = updateHtmlAssetRefs(source, cssFileName, jsFileName);
    const minified = passthrough.endsWith(".html")
      ? await minifyHtml(updated, {
          collapseWhitespace: true,
          removeComments: true,
          removeRedundantAttributes: true,
          removeScriptTypeAttributes: true,
          removeStyleLinkTypeAttributes: true,
          keepClosingSlash: true,
          minifyCSS: false,
          minifyJS: false,
        })
      : updated;
    await fs.mkdir(stagingDir, { recursive: true });
    await fs.writeFile(path.join(stagingDir, passthrough), minified, "utf8");
  }
}

async function buildPythonShim(cssFileName, jsFileName) {
  const source = await fs.readFile(path.join(srcDir, "__init__.py"), "utf8");
  const updated = hashed ? updatePythonStaticMap(source, cssFileName, jsFileName) : source;
  await fs.mkdir(stagingDir, { recursive: true });
  await fs.writeFile(path.join(stagingDir, "__init__.py"), updated, "utf8");
}

async function syncDir(sourceDir, targetDir) {
  await ensureCleanDir(targetDir);
  const entries = await fs.readdir(sourceDir, { withFileTypes: true });
  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      await fs.cp(sourcePath, targetPath, { recursive: true });
    } else {
      await fs.copyFile(sourcePath, targetPath);
    }
  }
}

async function main() {
  await ensureCleanDir(stagingDir);

  const copiedFiles = rootCopyFiles.filter((file) => !["__init__.py", "1.html", "index.html", "index2.html", "login.html", "subcontrol_app.html", "automation_config.html"].includes(file));
  for (const file of copiedFiles) {
    await copyFileIfPresent(file);
  }
  await copyDir("assets");
  await buildIconsManifest();

  const cssResult = await buildCss();
  const jsResult = await buildJs();

  await buildHtmlFiles(cssResult.fileName, jsResult.fileName);
  await buildPythonShim(cssResult.fileName, jsResult.fileName);

  const manifest = {
    mode: hashed ? "hashed" : "stable",
    generatedAt: new Date().toISOString(),
    files: {
      css: cssResult.fileName,
      js: jsResult.fileName,
      dashboardHtml: "1.html",
    },
    omittedPatterns: [
      "1_backup.*",
      "1_before_*",
      "1_step*_backup.css",
      "*.bak",
      "__pycache__",
      "scratch_*",
    ],
  };
  await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2), "utf8");

  await syncDir(stagingDir, publicDir);
  await syncDir(stagingDir, releaseDir);
  await fs.rm(stagingDir, { recursive: true, force: true });

  console.log(`Release build complete: ${publicDir}`);
  console.log(`Release mirror saved: ${releaseDir}`);
  console.log(`CSS: ${cssResult.fileName} (${cssResult.bytes} bytes)`);
  console.log(`JS : ${jsResult.fileName} (${jsResult.bytes} bytes)`);
  console.log(`Mode: ${manifest.mode}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
