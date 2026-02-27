"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import axios from "axios";
import "../../../../../globals.css";
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
  const [isMatching, setIsMatching] = useState<boolean>(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [matchInfo, setMatchInfo] = useState<{
    driverName: string;
    driverPhone: string;
    otp: string;
  } | null>(null);

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

  const stationId = params?.stationId as string | undefined;
  const destinationParam = params?.destination as string | undefined;

  const humanDestination = destinationParam
    ? destinationParam.replace(/\+/g, " ")
    : "";

  // Register rider when match page loads, once we know user and params
  useEffect(() => {
    if (!userId || role !== "rider") return;
    if (!stationId || !humanDestination) return;

    const register = async () => {
      try {
        await axios.post(
          "http://localhost:5001/registerRider",
          {
            station_id: stationId,
            destination: humanDestination,
          },
          { withCredentials: true }
        );
      } catch (err) {
        console.error("Failed to register rider", err);
      }
    };

    register();
  }, [userId, role, stationId, humanDestination]);

  // Initiate match once rider is authenticated
  useEffect(() => {
    if (!userId || role !== "rider") return;

    const initiate = async () => {
      setIsMatching(true);
      setMatchError(null);
      try {
        const response = await axios.post(
          "http://localhost:5001/initiateMatch",
          {},
          { withCredentials: true }
        );

        const data = response.data;
        if (!data.found) {
          setMatchInfo(null);
          setMatchError("No drivers available right now. Please try again shortly.");
        } else {
          setMatchInfo({
            driverName: data.driver_name ?? "",
            driverPhone: data.driver_phone ?? "",
            otp: data.otp ?? "",
          });
        }
      } catch (err) {
        console.error("Failed to initiate match", err);
        setMatchInfo(null);
        setMatchError("Failed to initiate match. Please refresh and try again.");
      } finally {
        setIsMatching(false);
      }
    };

    initiate();
  }, [userId, role]);

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        <section className="relative z-10 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/85 px-5 py-4 shadow-lg shadow-black/40 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-emerald-300/80">
              Rider match
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              {matchInfo ? "Driver found" : "Looking for a driver"}
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              {matchInfo
                ? "You have been matched with a driver. Review the trip details below."
                : "We are finding a driver for your trip."}
            </p>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              <span className="font-semibold">Start station ID:</span> {stationId}
            </p>
            {humanDestination && (
              <p className="mt-1 max-w-xl text-xs text-slate-300">
                <span className="font-semibold">Destination:</span> {humanDestination}
              </p>
            )}
            {matchInfo && (
              <div className="mt-4 rounded-xl border border-emerald-500/50 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-50 shadow-md shadow-emerald-500/20">
                <p className="text-[11px] uppercase tracking-[0.2em] text-emerald-300/80">
                  Assigned driver
                </p>
                <p className="mt-1 text-sm font-semibold">
                  {matchInfo.driverName || "Unnamed driver"}
                </p>
                <p className="mt-1 text-xs text-emerald-100/90">
                  Contact: <span className="font-mono">{matchInfo.driverPhone}</span>
                </p>
                <p className="mt-2 text-xs">
                  OTP for pickup:
                  <span className="ml-2 inline-flex items-center rounded-full bg-emerald-500 px-2 py-0.5 text-[11px] font-semibold text-slate-950 shadow-sm shadow-emerald-500/40">
                    {matchInfo.otp || "N/A"}
                  </span>
                </p>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-200">
            {matchInfo ? (
              <span className="rounded-full bg-emerald-600/20 px-3 py-1 text-emerald-200">
                Driver assigned
              </span>
            ) : matchError ? (
              <span className="rounded-full bg-red-600/20 px-3 py-1 text-red-200">
                {matchError}
              </span>
            ) : (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                <span>{isMatching ? "Searching for nearby drivers" : "Waiting to start match"}</span>
              </>
            )}
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
