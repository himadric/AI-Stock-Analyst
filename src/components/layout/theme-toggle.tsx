"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

// The `dark` class on <html> is the source of truth; the inline script in app/layout.tsx sets it before paint
function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getSnapshot() {
  return document.documentElement.classList.contains("dark");
}

// null on the server and during hydration, so the first client render matches the server HTML
function getServerSnapshot() {
  return null;
}

export function ThemeToggle() {
  const isDark = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      // Storage can throw in private browsing; the toggle still works for this page load
    }
  };

  if (isDark === null) {
    return (
      <Button variant="ghost" size="icon" aria-label="Toggle theme">
        <span className="h-5 w-5" />
      </Button>
    );
  }

  const label = isDark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={label} title={label}>
      {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </Button>
  );
}
