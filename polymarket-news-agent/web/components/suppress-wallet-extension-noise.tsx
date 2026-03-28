import Script from "next/script"

/**
 * MetaMask (and similar wallets) inject inpage.js into every page. On some setups it
 * throws "Failed to connect to MetaMask" / unhandled rejections that are unrelated to
 * this app. We don't use Web3 in the UI; this keeps Next dev overlay usable on localhost.
 */
export function SuppressWalletExtensionNoise() {
  return (
    <Script
      id="suppress-wallet-extension-rejections"
      strategy="beforeInteractive"
      dangerouslySetInnerHTML={{
        __html: `
(function () {
  function benign(reason) {
    try {
      var m = reason && (reason.message != null ? reason.message : reason);
      m = String(m || "");
      return (
        m.indexOf("MetaMask") !== -1 ||
        m.indexOf("Failed to connect to MetaMask") !== -1 ||
        m.indexOf("MetaMask extension not found") !== -1
      );
    } catch (e) {
      return false;
    }
  }
  window.addEventListener("unhandledrejection", function (e) {
    if (benign(e.reason)) e.preventDefault();
  });
})();
        `,
      }}
    />
  )
}
