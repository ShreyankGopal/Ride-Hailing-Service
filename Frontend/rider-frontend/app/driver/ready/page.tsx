"use client";
import dynamic from "next/dynamic";

const DriverLiveMap = dynamic(
  () => import("@/components/DriverLiveMap"),
  { ssr: false }
);
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import "../../globals.css";
import { LatLngExpression } from "leaflet";

/**
 * DriverReadyPage
 *
 * Screen shown after a driver goes online.
 * Displays a "searching for riders" header and a full-screen map placeholder
 * where real live-location tracking can be integrated later.
 */
export default function DriverReadyPage() {
  const router = useRouter();
  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [position, setPosition] = useState<LatLngExpression | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Basic auth guard using /me (same pattern as other driver pages)
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

  // Open WebSocket after user is known
  useEffect(() => {
    if (!userId || !role) return;

    const ws = new WebSocket("ws://localhost:5001/ws/driver/location");
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected for driver location streaming");
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected for driver location streaming");
    };

    ws.onerror = (event) => {
      console.error("WebSocket error for driver location streaming", event);
    };

    return () => {
      ws.close();
    };
  }, [userId, role]);
  const lastKnownRef = useRef<GeolocationPosition | null>(null);

  useEffect(() => {// this use effect streams the location to the backend with the help of web sockets every 3 seconds. 
    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(// navigator.geolocation.watchPosition is a browser API to get the current location. pos is a call back that we ahve written to update the last known location.
      // The api takes in the following functions
      // 1. Success callback
      // 2. Error callback
      // 3. Options
      (pos) => {
        console.log("Geolocation success", pos);
        lastKnownRef.current = pos;
      },
      (err) => {
        console.error("Geolocation error", {
          code: err.code,
          message: err.message,
        });
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 10000,
      }
    );

    const interval = setInterval(() => {
      if (!lastKnownRef.current) return;

      const pos = lastKnownRef.current;
      setPosition([pos.coords.latitude, pos.coords.longitude]);
      console.log("Emitted:", pos.coords.latitude, pos.coords.longitude);
    }, 3000);

    return () => {
      navigator.geolocation.clearWatch(watchId);
      clearInterval(interval);
    };
  }, []);

  // Stream location over WebSocket whenever it changes
  useEffect(() => {
    if (!position || !userId || !role) return;

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    try {
      const [lat, lng] = position as [number, number];
      ws.send(
        JSON.stringify({
          userId,
          role,
          lat,
          lng,
        })
      );
    } catch (err) {
      console.error("Failed to send location over WebSocket", err);
    }
  }, [position, userId, role]);


  if (isLoadingUser) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Preparing your driver session...</p>
      </div>
    );
  }

  if (!userId || role !== "driver") {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      {/* The outer container acts as a backdrop for the map */}
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        {/* Header with loading indicator */}
        <section className="relative z-10 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/85 px-5 py-4 shadow-lg shadow-black/40 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-sky-300/80">
              Driver status
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              Searching for riders
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              You are online and visible to riders in your area. This screen
              will show a live map with your location and nearby demand once
              integrated.
            </p>
          </div>

          {/* Simple loading/spinner indicator */}
          <div className="flex items-center gap-3 text-xs text-slate-200">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
            <span>Waiting for trip requests</span>
          </div>
        </section>

        {/* Map placeholder area */}
        <section className="relative mt-6 flex-1 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80">
          {/* Placeholder background for the map */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#0ea5e9_0,_transparent_45%),_radial-gradient(circle_at_bottom,_#22c55e_0,_transparent_45%)] opacity-40" />

          {/* Live driver map */}
          <div className="relative z-10 h-full w-full">
            {position && <DriverLiveMap position={position}/>}
          </div>
        </section>
      </main>
    </div>
  );
}
