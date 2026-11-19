(function () {

    "use strict";

    const config = document.getElementById(
        "play-session-config"
    );

    if (!config) {
        return;
    }

    const heartbeatUrl = config.dataset.heartbeatUrl;
    const endSessionUrl = config.dataset.endSessionUrl;
    const csrfToken = config.dataset.csrfToken;

    const gameRound = config.dataset.gameRound;

    // 定期通信の間隔（30秒）
    const HEARTBEAT_INTERVAL = 30000;

    let sessionId = null;
    let communicating = false;
    let firstPageView = true;

    let pendingEnd = false;
    let pendingResume = false;

    let internalNavigation = false;
    let navigationTimer = null;
    let pageLeaving = false;


    // ==========================================
    // ゲーム内の画面移動
    // ==========================================

        function markInternalNavigation() {

        console.log("[PlaySession] ゲーム内移動", window.location.href);

        internalNavigation = true;

        clearTimeout(navigationTimer);

        navigationTimer = setTimeout(function () {

            internalNavigation = false;

            if (document.hidden && !pageLeaving) {
                sendEndSession();
            }

        }, 10000);

    }

    window.markPlaySessionNavigation =
        markInternalNavigation;

        // ==========================================
    // ゲーム内のURLかどうかを判定
    // ==========================================

    function isInternalGameUrl(value) {

    const url = new URL(
        value,
        window.location.href
    );

    const gameRoot = new URL(
        "../",
        heartbeatUrlAbsolute()
    );

    if (url.origin !== window.location.origin) {
        return false;
    }

    // リアルタイム型
    if (gameRoot.pathname === "/realtime/") {
        return url.pathname.startsWith("/realtime/");
    }

    // ターン制
    const turnBasedPaths = [
        "/",
        "/ball_game/",
        "/food_game/",
        "/dodge_game/",
        "/dance_game/",
        "/timing_game/",
        "/count_game/"
    ];

    return turnBasedPaths.includes(url.pathname);
}

    function heartbeatUrlAbsolute() {

        return new URL(
            heartbeatUrl,
            window.location.href
        );

    }


    // ==========================================
    // リンクによるゲーム内の画面移動
    // ==========================================

    document.addEventListener(
        "click",
        function (event) {

            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey ||
                event.metaKey
            ) {
                return;
            }

            const link = event.target.closest("a[href]");

            if (!link) {
                return;
            }

            if (
                link.hasAttribute("download") ||
                (link.target && link.target !== "_self")
            ) {
                return;
            }

            const href = link.getAttribute("href");

            if (!href || href.startsWith("#")) {
                return;
            }

            if (isInternalGameUrl(link.href)) {

                markInternalNavigation();

            }

        }
    );


    // ==========================================
    // フォームによるゲーム内の画面移動
    // ==========================================

    document.addEventListener(
        "submit",
        function (event) {

            if (event.defaultPrevented) {
                return;
            }

            const form = event.target;

            if (form.target && form.target !== "_self") {
                return;
            }

            // ゲーム内移動として指定されたフォーム
            if (form.dataset.playNavigation === "true") {

                markInternalNavigation();

                return;
            }

            const action =
                event.submitter?.getAttribute("formaction")
                || form.action
                || window.location.href;

            if (isInternalGameUrl(action)) {

                markInternalNavigation();

            }

        }
    );


    // ==========================================
    // プレイ開始・継続の通知
    // ==========================================

    async function sendHeartbeat() {

        if (document.hidden || pageLeaving) {
            return;
        }

        if (communicating) {
            pendingResume = true;
            return;
        }

        communicating = true;
        pendingResume = false;

        const data = new URLSearchParams();
                data.set("game_round", gameRound);

        data.set(
            "csrfmiddlewaretoken",
            csrfToken
        );

        data.set(
            "page_view",
            firstPageView ? "1" : "0"
        );

        try {

            const response = await fetch(
                heartbeatUrl,
                {
                    method: "POST",
                    credentials: "same-origin",
                    body: data,
                    cache: "no-store",
                    redirect: "error",
                    keepalive: true
                }
            );

            if (response.ok) {

                const result = await response.json();

                if (result.ok) {

                    sessionId = result.session_id;

                    firstPageView = false;

                    console.log("[PlaySession] 開始・継続", {
                        sessionId: sessionId,
                        gameRound: gameRound,
                        url: window.location.href
                    });

                }

            }

        } catch (error) {

            console.warn(
                "プレイ時間の記録に失敗しました",
                error
            );

        } finally {

            communicating = false;

            if (pendingEnd) {

                pendingEnd = false;

                sendEndSession();

            } else if (
                pendingResume &&
                !document.hidden &&
                !pageLeaving
            ) {

                sendHeartbeat();

            }

        }

    }


    // ==========================================
    // プレイ終了の通知
    // ==========================================

    async function sendEndSession() {

        console.log("[PlaySession] 終了通知", {
            sessionId: sessionId,
            internalNavigation: internalNavigation,
            pageLeaving: pageLeaving,
            hidden: document.hidden,
            url: window.location.href
        });

        if (communicating) {

            pendingEnd = true;

            return;

        }

        if (sessionId === null) {

            if (!document.hidden && !pageLeaving) {
                sendHeartbeat();
            }

            return;

        }

        communicating = true;

        const data = new URLSearchParams();

        data.set(
            "csrfmiddlewaretoken",
            csrfToken
        );

        data.set(
            "session_id",
            String(sessionId)
        );

        sessionId = null;

        try {

            await fetch(
                endSessionUrl,
                {
                    method: "POST",
                    credentials: "same-origin",
                    body: data,
                    keepalive: true,
                    cache: "no-store",
                    redirect: "error"
                }
            );

        } catch (error) {

            console.warn(
                "プレイ終了の記録に失敗しました",
                error
            );

        } finally {

            communicating = false;

            pendingEnd = false;

            if (!document.hidden && !pageLeaving) {

                pendingResume = false;

                sendHeartbeat();

            }

        }

    }


    // ==========================================
    // 画面の表示・非表示
    // ==========================================

    document.addEventListener(
        "visibilitychange",
        function () {

            if (document.hidden) {

                pendingResume = false;

                if (!internalNavigation) {
                    sendEndSession();
                }

            } else {

                internalNavigation = false;

                clearTimeout(navigationTimer);

                sendHeartbeat();

            }

        }
    );


    // ==========================================
    // ページを閉じる・移動する
    // ==========================================

    window.addEventListener(
        "pagehide",
        function () {

            pageLeaving = true;

            pendingResume = false;

            clearTimeout(navigationTimer);

            if (!internalNavigation) {
                sendEndSession();
            }

        }
    );


    // ==========================================
    // ブラウザの戻る操作などによる再表示
    // ==========================================

    window.addEventListener(
        "pageshow",
        function (event) {

            if (event.persisted) {

                pageLeaving = false;

                internalNavigation = false;

                clearTimeout(navigationTimer);

                sendHeartbeat();

            }

        }
    );


    // ==========================================
    // プレイ開始
    // ==========================================

    sendHeartbeat();


    // ==========================================
    // 30秒ごとにプレイ時間を記録
    // ==========================================

    setInterval(
        sendHeartbeat,
        HEARTBEAT_INTERVAL
    );

})();