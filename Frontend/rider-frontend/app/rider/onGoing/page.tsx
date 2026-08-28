"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import "../../globals.css";
import { LatLngExpression } from "leaflet";

const DriverLiveMap = dynamic(
  () => import("@/components/DriverLiveMap"),
  { ssr: false }
);

interface TripInfo {
  trip_id: string;
  trip_status: string;
  driver_id: string;
  otp: string;
}

export default function RiderOnGoingPage() {
  const router = useRouter();

  const [isLoading, setIsLoading] = useState(true);
  const [tripInfo, setTripInfo] = useState<TripInfo | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [position, setPosition] = useState<LatLngExpression | null>(null);
  const [driverPosition, setDriverPosition] = useState<LatLngExpression | null>(null);
  const [driverName, setDriverName] = useState("");
  const [driverPhone, setDriverPhone] = useState("");

  // Auth + trip status check
  useEffect(() => {
    const init = async () => {
      try {
        // 1. Auth check
        const meRes = await axios.get("http://localhost:5001/me", {
          withCredentials: true,
        });
        const uid = meRes.data.user_id;
        const role = meRes.data.role;
        setUserId(uid);

        if (role !== "rider") {
          router.push("/login");
          return;
        }

        // 2. Fetch active trip
        const statusRes = await axios.get("http://localhost:5001/me/tripStatus", {
          withCredentials: true,
        });

        if (!statusRes.data.has_active_trip) {
          // No active trip — send back to booking
          router.push("/rider/booking");
          return;
        }

        setTripInfo({
          trip_id: statusRes.data.trip_id,
          trip_status: statusRes.data.trip_status,
          driver_id: statusRes.data.driver_id,
          otp: statusRes.data.otp,
        });
      } catch {
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, [router]);

  // GPS watch for rider's own position
  useEffect(() => {
    if (!navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (pos) => setPosition([pos.coords.latitude, pos.coords.longitude]),
      console.error,
      { enableHighAccuracy: true }
    );
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  // Poll driver position every 3 s
  useEffect(() => {
    if (!tripInfo?.driver_id) return;
    const driverId = tripInfo.driver_id;

    const fetchPos = async () => {
      try {
        const res = await axios.post(
          "http://localhost:5001/driverPosition",
          { driver_id: driverId },
          { withCredentials: true }
        );
        if (res.data.found) {
          setDriverPosition([res.data.latitude, res.data.longitude]);
        }
      } catch { /* ignore */ }
    };

    fetchPos();
    const interval = setInterval(fetchPos, 3000);
    return () => clearInterval(interval);
  }, [tripInfo?.driver_id]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Loading your trip...</p>
      </div>
    );
  }

  if (!tripInfo) return null;

  const statusLabel =
    tripInfo.trip_status === "matched" ? "Driver on the way" : "Trip in progress";
  const statusColor =
    tripInfo.trip_status === "matched" ? "text-amber-300" : "text-emerald-300";
  const statusBg =
    tripInfo.trip_status === "matched"
      ? "bg-amber-500/15 border-amber-500/40"
      : "bg-emerald-500/15 border-emerald-500/40";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        {/* Header */}
        <section className={`relative z-10 flex flex-col gap-3 rounded-2xl border ${statusBg} bg-slate-950/85 px-5 py-4 shadow-lg shadow-black/40 md:flex-row md:items-start md:justify-between`}>
          <div className="flex-1">
            <p className={`text-xs uppercase tracking-[0.25em] ${statusColor}`}>
              {tripInfo.trip_status === "matched" ? "Ride matched" : "Ride ongoing"}
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              {statusLabel}
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              {tripInfo.trip_status === "matched"
                ? "Your driver is heading to your station. Share the OTP below when they arrive."
                : "Your trip is in progress. Enjoy the ride!"}
            </p>

            {/* Trip details */}
            <div className={`mt-4 rounded-xl border ${statusBg} px-4 py-3 text-xs text-slate-100 shadow-md`}>
              <p className={`text-[11px] uppercase tracking-[0.2em] ${statusColor}`}>
                Trip details
              </p>
              <div className="mt-2 flex flex-col gap-1.5">
                <p>
                  <span className="font-semibold text-slate-300">Trip ID:</span>{" "}
                  <span className="font-mono">{tripInfo.trip_id}</span>
                </p>
                <p>
                  <span className="font-semibold text-slate-300">OTP for driver:</span>{" "}
                  <span className="ml-1 inline-flex items-center rounded-full bg-emerald-500 px-2.5 py-0.5 font-mono text-[13px] font-bold text-slate-950">
                    {tripInfo.otp}
                  </span>
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Show this OTP to your driver when they arrive at your pickup station.
                </p>
              </div>
            </div>
          </div>

          {/* Status badge */}
          <div className="flex items-center gap-2 self-start">
            {tripInfo.trip_status === "matched" && (
              <>
                <div className="h-3 w-3 animate-pulse rounded-full bg-amber-400" />
                <span className="text-xs text-amber-300">Driver en route</span>
              </>
            )}
            {tripInfo.trip_status === "OnGoing" && (
              <>
                <div className="h-3 w-3 rounded-full bg-emerald-400" />
                <span className="text-xs text-emerald-300">Trip started</span>
              </>
            )}
          </div>
        </section>

        {/* Live map */}
        <section className="relative mt-6 flex-1 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80" style={{ minHeight: "400px" }}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#22c55e_0,_transparent_45%),_radial-gradient(circle_at_bottom,_#0ea5e9_0,_transparent_45%)] opacity-30" />
          <div className="relative z-10 h-full w-full">
            {position && (
              <DriverLiveMap
                position={position}
                driverPosition={driverPosition}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
