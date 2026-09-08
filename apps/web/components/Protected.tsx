"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { currentUser, refreshCurrentUser } from "@/lib/auth";

export default function Protected({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    void refreshCurrentUser()
      .then((user) => {
        if (!active) return;
        if (!user) {
          router.replace("/login");
          return;
        }
        setReady(true);
      })
      .catch(() => {
        if (!active) return;
        if (currentUser()) {
          setReady(true);
        } else {
          router.replace("/login");
        }
      });
    return () => {
      active = false;
    };
  }, [router]);

  if (!ready) {
    return <div className="screen-center"><div className="spinner" aria-label="Loading" /></div>;
  }
  return <>{children}</>;
}
