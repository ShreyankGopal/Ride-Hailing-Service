"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import axios from "axios";
import "../../globals.css";

/**
 * DriverHomePage
 *
 * Landing screen for drivers after login.
 * Contains shortcuts to key driver flows.
 */
export default function DriverHomePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    /**
     * Validate authentication using the JWT cookie by calling
     * the backend /me endpoint. If unauthorized, redirect
     * the user back to the login screen.
     */
    const fetchCurrentUser = async () => {
      try {
        const response = await axios.get("http://localhost:5001/me", {
          withCredentials: true,
        });

        setUserId(response.data.user_id ?? null);
        setRole(response.data.role ?? null);
      } catch (error) {
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    fetchCurrentUser();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Loading your driver dashboard...</p>
      </div>
    );
  }

  if (!userId || role !== "driver") {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-sky-900 text-slate-50">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-10 px-4 py-10 md:px-8">
        {/* Top header / status section */}
        <section className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-sky-300/80">
              Driver Dashboard
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Stay online and find more riders
            </h1>
            <p className="mt-3 max-w-xl text-sm text-slate-300">
              Go online, manage your profile, and track your daily earnings in a
              single, focused view.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <div className="rounded-2xl border border-sky-400/40 bg-gradient-to-br from-sky-500/20 via-slate-900 to-slate-950 px-6 py-4 shadow-lg shadow-sky-500/30">
              <p className="text-xs font-medium text-sky-100/90">
                Today&apos;s summary (placeholder)
              </p>
              <div className="mt-2 flex gap-8 text-xs">
                <div>
                  <p className="text-2xl font-semibold text-sky-300">₹1,540</p>
                  <p className="mt-1 text-[11px] text-slate-200">Estimated earnings</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold text-sky-300">7</p>
                  <p className="mt-1 text-[11px] text-slate-200">Completed trips</p>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  await axios.post(
                    "http://localhost:5001/logout",
                    {},
                    { withCredentials: true },
                  );
                } finally {
                  router.push("/login");
                }
              }}
              className="self-end rounded-full border border-slate-700 bg-slate-900/70 px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-md shadow-black/40 transition hover:bg-slate-800"
            >
              Log out
            </button>
          </div>
        </section>

        {/* Main action grid */}
        <section className="grid gap-6 md:grid-cols-3">
          {/* Search for riders card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-sky-400/60 hover:shadow-sky-500/30">
            <div>
              <h2 className="text-lg font-semibold">Search for riders</h2>
              <p className="mt-2 text-xs text-slate-300">
                Go online and get matched with riders requesting trips near you.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-sky-300/80">
                {/* TODO: Replace href with actual driver matching route */}
                Find nearby requests
              </span>
              <Link
                href="#" // TODO: point to driver search/matching route
                className="rounded-full bg-sky-500 px-4 py-1.5 text-xs font-semibold text-slate-950 shadow-md shadow-sky-500/40 transition group-hover:bg-sky-400"
              >
                Go online
              </Link>
            </div>
          </div>

          {/* Driver profile card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-sky-400/60 hover:shadow-sky-500/30">
            <div>
              <h2 className="text-lg font-semibold">Profile &amp; vehicle</h2>
              <p className="mt-2 text-xs text-slate-300">
                Edit your profile, vehicle details, and available service areas.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-sky-300/80">
                {/* TODO: Replace href with actual driver profile route */}
                Keep your info up to date
              </span>
              <Link
                href="#" // TODO: point to driver profile route
                className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-md shadow-black/40 transition group-hover:bg-slate-700"
              >
                Open profile
              </Link>
            </div>
          </div>

          {/* Earnings overview card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-sky-400/60 hover:shadow-sky-500/30">
            <div>
              <h2 className="text-lg font-semibold">Earnings &amp; history</h2>
              <p className="mt-2 text-xs text-slate-300">
                Review your earnings by day or week and see detailed trip
                breakdowns.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-sky-300/80">
                {/* TODO: Replace href with actual earnings route */}
                Analyze your performance
              </span>
              <Link
                href="#" // TODO: point to earnings/history route
                className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-md shadow-black/40 transition group-hover:bg-slate-700"
              >
                View earnings
              </Link>
            </div>
          </div>
        </section>

        {/* Secondary section: status & tips */}
        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <h3 className="text-sm font-semibold">Availability status</h3>
            <p className="mt-2 text-xs text-slate-300">
              Toggle between online and offline (placeholder control). We&apos;ll
              hook this up to real driver status updates later.
            </p>
            <div className="mt-4 flex items-center gap-3 text-xs">
              <button className="rounded-full bg-emerald-500 px-4 py-1.5 font-semibold text-slate-950 shadow-md shadow-emerald-500/40 transition hover:bg-emerald-400">
                {/* TODO: wire to driver status update route */}
                Go online
              </button>
              <button className="rounded-full border border-slate-600 px-4 py-1.5 font-semibold text-slate-100 hover:bg-slate-800">
                Go offline
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-sky-600/25 via-slate-950 to-slate-950 p-5">
            <h3 className="text-sm font-semibold">Driving tips &amp; quality</h3>
            <p className="mt-2 text-xs text-slate-100">
              Maintain a high rating, follow safe driving practices, and learn
              how to get more trip requests during peak hours.
            </p>
            <div className="mt-4 flex flex-wrap gap-3 text-xs">
              <button className="rounded-full bg-sky-500 px-4 py-1.5 font-semibold text-slate-950 shadow-md shadow-sky-500/40 transition hover:bg-sky-400">
                {/* TODO: wire to driver tips/guide route */}
                View tips
              </button>
              <button className="rounded-full border border-sky-400/70 bg-transparent px-4 py-1.5 font-semibold text-sky-200 hover:bg-sky-500/10">
                {/* TODO: wire to support/feedback route */}
                Contact support
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
