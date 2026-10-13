/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const resolveFilename = Module._resolveFilename;
Module._resolveFilename = function (specifier, ...args) {
  if (specifier.startsWith('@/')) {
    specifier = path.join(__dirname, '../src', specifier.slice(2));
  }
  return resolveFilename.call(this, specifier, ...args);
};

require.extensions['.ts'] = (module, filename) => {
  const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
    fileName: filename,
  });
  module._compile(outputText, filename);
};
