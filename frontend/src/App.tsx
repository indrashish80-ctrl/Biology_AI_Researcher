import { useCallback, useEffect, useState } from "react";
import { Nav, type Route } from "./components/Nav";
import { Landing } from "./components/Landing";
import { Console } from "./components/Console";
import { KeyManager } from "./components/KeyManager";

function routeFromHash(): Route {
  return window.location.hash.replace(/^#\/?/, "") === "console" ? "console" : "landing";
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [keysOpen, setKeysOpen] = useState(false);

  useEffect(() => {
    const onHash = () => {
      setRoute(routeFromHash());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = useCallback((r: Route) => {
    window.location.hash = r === "landing" ? "/" : "/console";
  }, []);

  const openKeys = useCallback(() => setKeysOpen(true), []);

  return (
    <div className="relative min-h-screen bg-void">
      <Nav route={route} go={go} openKeys={openKeys} />
      {route === "console" ? (
        <Console goLanding={() => go("landing")} openKeys={openKeys} />
      ) : (
        <Landing enterConsole={() => go("console")} openKeys={openKeys} />
      )}
      {keysOpen && <KeyManager onClose={() => setKeysOpen(false)} />}
    </div>
  );
}
