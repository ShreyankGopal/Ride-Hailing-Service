"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import "../../../globals.css";
import { LatLngExpression } from "leaflet";

const DriverLiveMap = dynamic(
  () => import("@/components/DriverLiveMap"),
  { ssr: false }
);

interface TripInfo {
  trip_id: string;
  trip_status: string;
  rider_id: string;
}

export default function DriverOnGoingPage() {
  const router = useRouter();

  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tripInfo, setTripInfo] = useState<TripInfo | null>(null);
  const [position, setPosition] = useState<LatLngExpression | null>(null);

  // Complete trip state
  const [isCompleting, setIsCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const lastKnownRef = useRef<GeolocationPosition | null>(null);

  // Auth + trip status check
  useEffect(() => {
    const init = async () => {
      try {
        const meRes = await axios.get("http://localhost:5001/me", {
          withCredentials: true,
        });
        const uid = meRes.data.user_id;
        const r = meRes.data.role;
        setUserId(uid);
        setRole(r);

        if (r !== "driver") {
          router.push("/login");
          return;
        }

        const statusRes = await axios.get("http://localhost:5001/me/tripStatus", {
          withCredentials: true,
        });

        if (!statusRes.data.has_active_trip) {
          // No active trip — go back to driver home
          router.push("/driver/home");
          return;
        }

        setTripInfo({
          trip_id: statusRes.data.trip_id,
          trip_status: statusRes.data.trip_status,
          rider_id: statusRes.data.rider_id,
        });
      } catch {
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, [router]);

  // Open location streaming WebSocket
  useEffect(() => {
    if (!userId || !role) return;
    const ws = new WebSocket("ws://localhost:5001/ws/driver/location");
    wsRef.current = ws;
    ws.onopen = () => console.log("Driver location WS connected");
    ws.onclose = () => console.log("Driver location WS disconnected");
    return () => ws.close();
  }, [userId, role]);

  // GPS watch
  useEffect(() => {
    if (!navigator.geolocation) return;
    const watchId = navigator.geolocation.watchPosition(
      (pos) => { lastKnownRef.current = pos; },
      (err) => console.error("Geolocation error", err),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }
    );
    const interval = setInterval(() => {
      if (!lastKnownRef.current) return;
      const pos = lastKnownRef.current;
      setPosition([pos.coords.latitude, pos.coords.longitude]);
    }, 3000);
    return () => {
      navigator.geolocation.clearWatch(watchId);
      clearInterval(interval);
    };
  }, []);

  // Stream location over WebSocket
  useEffect(() => {
    if (!position || !userId || !role) return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      const [lat, lng] = position as [number, number];
      ws.send(JSON.stringify({ userId, role, lat, lng }));
    } catch (err) {
      console.error("Failed to send location", err);
    }
  }, [position, userId, role]);

  // Complete trip handler
  const handleCompleteTrip = async () => {
    setIsCompleting(true);
    setCompleteError(null);
    try {
      await axios.post(
        "http://localhost:5001/completeTrip",
        {},
        { withCredentials: true }
      );
      setCompleted(true);
      // Give user a moment to see the success state, then go home
      setTimeout(() => router.push("/driver/home"), 2000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Failed to complete trip. Please try again.";
      setCompleteError(detail);
    } finally {
      setIsCompleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Loading your active trip...</p>
      </div>
    );
  }

  if (!tripInfo) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        {/* Header */}
        <section className="relative z-10 flex flex-col gap-3 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-5 py-5 shadow-lg shadow-black/40 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <p className="text-xs uppercase tracking-[0.25em] text-emerald-300/80">
              Trip active
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              Trip in progress
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              Your trip is underway. Click "Complete Trip" once you've dropped off the passenger.
            </p>

            {/* Trip ID */}
            <div className="mt-4 rounded-xl border border-emerald-500/30 bg-slate-900/60 px-4 py-3 text-xs">
              <p className="text-[11px] uppercase tracking-[0.2em] text-emerald-300/80">
                Trip info
              </p>
              <p className="mt-1.5">
                <span className="font-semibold text-slate-300">Trip ID:</span>{" "}
                <span className="font-mono text-slate-100">{tripInfo.trip_id}</span>
              </p>
              <p className="mt-1">
                <span className="font-semibold text-slate-300">Status:</span>{" "}
                <span className="inline-flex items-center rounded-full bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                  {tripInfo.trip_status}
                </span>
              </p>
            </div>

            {/* Complete Trip button */}
            <div className="mt-5">
              {completed ? (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-3 text-emerald-300">
                  <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span className="font-semibold">Trip completed! Redirecting...</span>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <button
                    id="complete-trip-btn"
                    onClick={handleCompleteTrip}
                    disabled={isCompleting}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-emerald-500/30 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60 md:w-auto"
                  >
                    {isCompleting && (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                    )}
                    Complete Trip
                  </button>
                  {completeError && (
                    <p className="text-xs text-red-400">{completeError}</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Live status indicator */}
          <div className="flex items-center gap-2 self-start">
            <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-400" />
            <span className="text-xs text-emerald-300">OnGoing</span>
          </div>
        </section>

        {/* Live driver map */}
        <section className="relative mt-6 flex-1 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80" style={{ minHeight: "400px" }}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#0ea5e9_0,_transparent_45%),_radial-gradient(circle_at_bottom,_#22c55e_0,_transparent_45%)] opacity-40" />
          <div className="relative z-10 h-full w-full">
            {position && (
              <DriverLiveMap
                position={position}
                riderPosition={null}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
