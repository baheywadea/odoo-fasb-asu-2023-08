/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
console.log("✅ crypto_payment_page.js LOADED");

// WalletConnect project id
const WC_PROJECT_ID = "470172bafc95a7d19845d256955ec141";

// guards
let _inited = false;
let _pollingStarted = false;
let _wcBound = false;

function initCryptoPaymentPage() {
    if (_inited) return;
    _inited = true;

    const wrap = document.getElementById("wrap");
    if (!wrap) {
        console.warn("wrap not found");
        return;
    }

    console.log("wrap found", wrap.dataset);

    setupCopyButtons();

    const txId = wrap.dataset.txId;
    const token = wrap.dataset.token;

    console.log("txId/token", txId, token);

    if (txId && token) {
        startCryptoPolling(parseInt(txId, 10), token);
        setupWalletConnect(parseInt(txId, 10), token);
    } else {
        console.warn("Missing txId or token on #wrap dataset");
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCryptoPaymentPage);
} else {
    initCryptoPaymentPage();
}

function startCryptoPolling(txId, token) {
    if (_pollingStarted) return;
    _pollingStarted = true;

    const box = document.getElementById("crypto_status_box");
    const setStatus = (cls, text) => {
        if (!box) return;
        box.className = `alert ${cls} mb-0`;
        box.textContent = text;
    };

    const poll = async () => {
        try {
            const res = await rpc(`/crypto/status/${txId}`, { token });
            if (res && res.paid) {
                setStatus("alert-success", "Payment confirmed. Redirecting…");
                window.location.href = "/payment/status";
                return;
            }
            setStatus("alert-info", "Waiting for payment confirmation…");
        } catch (e) {
            setStatus("alert-warning", "Unable to check payment right now…");
        }
        setTimeout(poll, 2500);
    };

    poll();
}

function setupCopyButtons() {
    const buttons = document.querySelectorAll("[data-copy]");
    console.log("copy buttons found:", buttons.length);

    buttons.forEach((btn) => {
        if (btn.dataset.copyBound === "1") return;
        btn.dataset.copyBound = "1";

        btn.addEventListener("click", async () => {
            const val = btn.getAttribute("data-copy") || "";
            try {
                await navigator.clipboard.writeText(val);
                const old = btn.textContent;
                btn.textContent = "Copied";
                setTimeout(() => (btn.textContent = old), 900);
            } catch (e) {
                console.warn("clipboard failed", e);
            }
        });
    });
}

/**
 * WalletConnect provider global:
 * With our vendored UMD, it must exist on window.
 */
function getEthereumProvider() {
    // most common
    if (window.WalletConnectEthereumProvider?.init) return window.WalletConnectEthereumProvider;
    if (window.WalletConnectEthereumProvider?.default?.init) return window.WalletConnectEthereumProvider.default;

    // fallback
    if (window.EthereumProvider?.init) return window.EthereumProvider;
    if (window.ethereumProvider?.init) return window.ethereumProvider;

    return null;
}

function assertWalletConnectReady() {
    const provider = getEthereumProvider();
    const hasQR = typeof window.QRCode === "function";

    return {
        ok: !!provider && hasQR,
        provider,
        hasQR,
    };
}

function setupWalletConnect(txId, token) {
    if (_wcBound) return;
    _wcBound = true;

    const btn = document.getElementById("wc_connect_btn");
    const box = document.getElementById("wc_qr_box");
    const hint = document.getElementById("wc_qr_hint");
    const wcStatus = document.getElementById("wc_status");

    if (!btn || !box) {
        console.warn("❌ WalletConnect UI not found (wc_connect_btn / wc_qr_box).");
        return;
    }

    const setWCStatus = (text) => {
        if (wcStatus) wcStatus.textContent = text;
        console.log("[WC]", text);
    };

    // Hard check (no lazy load): libs must be ready from assets.xml
    const ready = assertWalletConnectReady();
    if (!ready.ok) {
        console.warn("❌ WC libs not ready at page load:", ready);
        setWCStatus("WalletConnect libraries not loaded. Check assets.xml (UMD + qrcodejs).");
        return;
    }

    if (!WC_PROJECT_ID) {
        setWCStatus("Missing WalletConnect projectId.");
        return;
    }

    btn.addEventListener("click", async () => {
        const oldText = btn.textContent;
        btn.disabled = true;

        try {
            btn.textContent = "Generating WalletConnect QR…";
            setWCStatus("Preparing intent…");

            // ✅ IMPORTANT: use backticks (template literal)
            const intent = await rpc(`/crypto/intent/${txId}`, { token });
            if (!intent?.ok) throw new Error(intent?.error || "intent_error");

            const chainId = Number(intent.chainId);
            const to = intent.to;
            const valueWeiStr = String(intent.valueWei || "0");
            const valueHex = "0x" + BigInt(valueWeiStr).toString(16);

            setWCStatus(`Intent loaded. ChainId=${chainId}`);

            const EthereumProvider = getEthereumProvider();
            if (!EthereumProvider?.init) throw new Error("wc_provider_init_missing");

            // Init WC provider
            const provider = await EthereumProvider.init({
                projectId: WC_PROJECT_ID,
                chains: [chainId],
                showQrModal: false,
                methods: ["eth_sendTransaction", "eth_accounts"],
                events: ["accountsChanged", "chainChanged", "disconnect"],
            });

            // Connect -> get wc URI -> render QR
            const wcUri = await provider.connect();

            box.innerHTML = "";
            box.style.display = "block";
            if (hint) hint.style.display = "none";

            new window.QRCode(box, {
                text: wcUri,
                width: 280,
                height: 280,
            });

            btn.textContent = "Scan QR with your wallet…";
            setWCStatus("QR generated. Waiting for wallet connection…");

            // Wait accounts (connected)
            const accounts = await provider.request({ method: "eth_accounts" });
            const from = accounts?.[0];
            if (!from) throw new Error("no_account");

            btn.textContent = "Approve payment in wallet…";
            setWCStatus(`Connected: ${from}`);

            // Send tx
            const txHash = await provider.request({
                method: "eth_sendTransaction",
                params: [{ from, to, value: valueHex, data: "0x" }],
            });

            setWCStatus(`Transaction sent: ${txHash}`);

            // Optional store hash (safe if route exists)
            try {
                await rpc(`/crypto/wc_tx/${txId}`, {
                    token,
                    tx_hash: txHash,
                    from_address: from,
                });
            } catch (e) {
                // not fatal
                console.warn("Failed to store tx hash", e);
            }

            btn.textContent = "Transaction sent. Waiting confirmation…";
            btn.disabled = true;
        } catch (e) {
            console.warn("WalletConnect error", e);
            setWCStatus("WalletConnect failed. Try again.");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    });
}
