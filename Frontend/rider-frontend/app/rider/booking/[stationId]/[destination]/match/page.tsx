"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import axios from "axios";
import "../../../../globals.css";
import { LatLngExpression } from "leaflet";

const DriverLiveMap = dynamic(
  () => import("@/components/DriverLiveMap"),
  { ssr: false }
);

export default function RiderMatchPage() {
  const router = useRouter();
  const params = useParams();

  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [position, setPosition] = useState<LatLngExpression | null>(null);

  const lastKnownRef = useRef<GeolocationPosition | null>(null);

  // Auth via /me
  useEffect(() => {
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
        setIsLoadingUser(false);
      }
    };

    fetchCurrentUser();
  }, [router]);

  // Basic GPS polling similar to DriverReadyPage (but no WebSocket streaming)
  useEffect(() => {
    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        lastKnownRef.current = pos;
      },
      console.error,
      { enableHighAccuracy: true }
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

  if (isLoadingUser) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Preparing your match screen...</p>
      </div>
    );
  }

  if (!userId || role !== "rider") {
    return null;
  }

  const stationId = params?.stationId as string | undefined;
  const destinationParam = params?.destination as string | undefined;

  const humanDestination = destinationParam
    ? destinationParam.replace(/\+/g, " ")
    : "";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        <section className="relative z-10 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/85 px-5 py-4 shadow-lg shadow-black/40 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-emerald-300/80">
              Rider match
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              Looking for a driver
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              We are finding a driver for your trip.
            </p>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              <span className="font-semibold">Start station ID:</span> {stationId}
            </p>
            {humanDestination && (
              <p className="mt-1 max-w-xl text-xs text-slate-300">
                <span className="font-semibold">Destination:</span> {humanDestination}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-200">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
            <span>Searching for nearby drivers</span>
          </div>
        </section>

        <section className="relative mt-6 flex-1 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#22c55e_0,_transparent_45%),_radial-gradient(circle_at_bottom,_#0ea5e9_0,_transparent_45%)] opacity-40" />

          <div className="relative z-10 h-full w-full">
            {position && <DriverLiveMap position={position} />}
          </div>
        </section>
      </main>
    </div>
  );
}
