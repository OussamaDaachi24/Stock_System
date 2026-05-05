const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("stockApi", {
  platform: process.platform,
});
