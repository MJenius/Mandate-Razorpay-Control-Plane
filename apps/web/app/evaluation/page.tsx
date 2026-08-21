"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function EvaluationRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/eval");
  }, [router]);
  return null;
}
