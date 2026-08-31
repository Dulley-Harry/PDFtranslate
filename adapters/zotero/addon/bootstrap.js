"use strict";

let pdftranslatePlugin = null;

async function startup({ id, version, rootURI }) {
  Services.scriptloader.loadSubScript(rootURI + "content/plugin.js", globalThis);
  pdftranslatePlugin = new PDFtranslateZoteroPlugin({ id, version, rootURI });
  Zotero.PDFtranslate = pdftranslatePlugin;
  await pdftranslatePlugin.startup();
}

async function shutdown() {
  if (pdftranslatePlugin) {
    await pdftranslatePlugin.shutdown();
  }
  pdftranslatePlugin = null;
  if (typeof Zotero !== "undefined" && Zotero.PDFtranslate) {
    delete Zotero.PDFtranslate;
  }
}

function install() {}
function uninstall() {}

function onMainWindowLoad({ window }) {
  pdftranslatePlugin?.onMainWindowLoad(window);
}

function onMainWindowUnload({ window }) {
  pdftranslatePlugin?.onMainWindowUnload(window);
}
