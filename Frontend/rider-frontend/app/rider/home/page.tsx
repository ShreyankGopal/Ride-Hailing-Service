"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import axios from "axios";
import "../../globals.css";
/**
 * RiderHomePage
 *
 * Landing screen for riders after login.
 * Contains shortcuts to the main rider flows.
 */
export default function RiderHomePage() {
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
        // On any auth error, send the user to the login page.
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    fetchCurrentUser();
  }, [router]);

  // Optional loading state while we validate the JWT.
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Loading your rider dashboard...</p>
      </div>
    );
  }

  // If for some reason we have no user even after loading, rely on the
  // redirect above; render nothing here.
  if (!userId || role !== "rider") {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-900 text-slate-50">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-10 px-4 py-10 md:px-8">
        {/* Top header / welcome section */}
        <section className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-emerald-300/80">
              Rider Dashboard
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Plan your next ride with ease
            </h1>
            <p className="mt-3 max-w-xl text-sm text-slate-300">
              Quickly book rides, manage your profile, and keep track of your
              upcoming and past trips. Everything you need in one place.
            </p>
          </div>
          
          <div className="flex flex-col gap-3">
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
            <div className="rounded-2xl border border-emerald-400/30 bg-gradient-to-br from-emerald-500/20 via-slate-900 to-slate-950 px-6 py-4 shadow-lg shadow-emerald-500/20">
              <p className="text-xs font-medium text-emerald-200/90">
                Estimated pickup in your area
              </p>
              <p className="mt-1 text-3xl font-semibold text-emerald-300">4–7 min</p>
              <p className="mt-2 text-[11px] text-slate-300">
                Live estimates based on active drivers nearby.
              </p>
            </div>
            
          </div>
        </section>

        {/* Main action grid */}
        <section className="grid gap-6 md:grid-cols-3">
          
          {/* Book Ride card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-emerald-400/60 hover:shadow-emerald-500/30">
            <div>
              <h2 className="text-lg font-semibold">Book a ride</h2>
              <p className="mt-2 text-xs text-slate-300">
                Set your pickup and drop-off locations and get matched with a
                nearby driver.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-emerald-300/80">
                {/* TODO: Replace href with actual booking route */}
                Quick ride booking
              </span>
              <Link
                href="/rider/booking" // TODO: point to rider booking route
                className="rounded-full bg-emerald-500 px-4 py-1.5 text-xs font-semibold text-slate-950 shadow-md shadow-emerald-500/40 transition group-hover:bg-emerald-400"
              >
                Book now
              </Link>
            </div>
          </div>

          {/* Profile card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-emerald-400/60 hover:shadow-emerald-500/30">
            <div>
              <h2 className="text-lg font-semibold">Profile &amp; payments</h2>
              <p className="mt-2 text-xs text-slate-300">
                Manage your personal details, saved locations and payment
                methods.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-emerald-300/80">
                {/* TODO: Replace href with actual rider profile route */}
                View and edit your profile
              </span>
              <Link
                href="/rider/profile" // TODO: point to rider profile route
                className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-md shadow-black/40 transition group-hover:bg-slate-700"
              >
                Open profile
              </Link>
            </div>
          </div>

          {/* Trips / History card */}
          <div className="group flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-lg shadow-black/40 transition hover:border-emerald-400/60 hover:shadow-emerald-500/30">
            <div>
              <h2 className="text-lg font-semibold">Trips &amp; activity</h2>
              <p className="mt-2 text-xs text-slate-300">
                See your upcoming rides, past trips, and invoices in one view.
              </p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-[11px] text-emerald-300/80">
                {/* TODO: Replace href with actual trips route */}
                Track your ride history
              </span>
              <Link
                href="/rider/trips" // TODO: point to rider trips route
                className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-md shadow-black/40 transition group-hover:bg-slate-700"
              >
                View trips
              </Link>
            </div>
          </div>
        </section>

        {/* Secondary section for filler / stats */}
        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <h3 className="text-sm font-semibold">Quick stats</h3>
            <div className="mt-4 grid grid-cols-3 gap-4 text-center text-xs">
              <div>
                <p className="text-2xl font-semibold text-emerald-300">12</p>
                <p className="mt-1 text-[11px] text-slate-300">Trips this month</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-emerald-300">4.9</p>
                <p className="mt-1 text-[11px] text-slate-300">Avg rating</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-emerald-300">₹820</p>
                <p className="mt-1 text-[11px] text-slate-300">Total spend</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-emerald-600/30 via-slate-950 to-slate-950 p-5">
            <h3 className="text-sm font-semibold">Safety &amp; support</h3>
            <p className="mt-2 text-xs text-slate-100">
              Access emergency contacts, safety tips, and 24x7 support for any
              issues with your rides.
            </p>
            <div className="mt-4 flex flex-wrap gap-3 text-xs">
              <button className="rounded-full bg-emerald-500 px-4 py-1.5 font-semibold text-slate-950 shadow-md shadow-emerald-500/40 transition hover:bg-emerald-400">
                {/* TODO: wire to in-app support/help route */}
                Get help
              </button>
              <button className="rounded-full border border-emerald-400/70 bg-transparent px-4 py-1.5 font-semibold text-emerald-200 hover:bg-emerald-500/10">
                {/* TODO: wire to safety center route */}
                Safety center
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
