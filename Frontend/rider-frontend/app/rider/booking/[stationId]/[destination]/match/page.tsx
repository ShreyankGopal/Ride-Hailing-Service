"use client";
// in next js we do not have ueNavigate instead we have useRouter imported from next/navigation

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, useCallback } from "react";
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
    driverID: string;
    driverName: string;
    driverPhone: string;
    otp: string;
  } | null>(null);
  const [driverPosition, setDriverPosition] = useState<LatLngExpression | null>(null);
  const [showCancelPrompt, setShowCancelPrompt] = useState(false);

  const lastKnownRef = useRef<GeolocationPosition | null>(null);
  const notifWsRef = useRef<WebSocket | null>(null);

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

  // Basic GPS polling
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

  // Register rider when match page loads
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

  // Connect to rider notification WebSocket BEFORE initiating match
  useEffect(() => {
    if (!userId || role !== "rider") return;

    const ws = new WebSocket(`ws://localhost:5001/ws/rider/notifications/${userId}`);
    notifWsRef.current = ws;

    ws.onopen = () => {
      console.log("Rider notification WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Rider notification received:", data);

        if (data.notification_type === "match_found") {
          // Navigate immediately to the onGoing screen.
          // The onGoing page will fetch trip details via /me/tripStatus.
          router.push("/rider/onGoing");
        } else if (data.notification_type === "no_driver_found") {
          setMatchInfo(null);
          setMatchError("No drivers available right now. Please try again shortly.");
          setIsMatching(false);
        }
      } catch (e) {
        console.error("Failed to parse notification", e);
      }
    };

    ws.onclose = () => {
      console.log("Rider notification WebSocket disconnected");
    };

    return () => {
      ws.close();
    };
  }, [userId, role]);

  // Queue match request (fire-and-forget, returns 202)
  useEffect(() => {
    if (!userId || role !== "rider") return;

    const initiate = async () => {
      setIsMatching(true);
      setMatchError(null);
      try {
        await axios.post(
          "http://localhost:5001/initiateMatch",
          {},
          { withCredentials: true }
        );
        // 202 returned — now waiting for WebSocket notification
        console.log("Match request queued, waiting for WebSocket notification...");
      } catch (err) {
        console.error("Failed to initiate match", err);
        setMatchInfo(null);
        setMatchError("Failed to initiate match. Please refresh and try again.");
        setIsMatching(false);
      }
    };

    initiate();
  }, [userId, role]);

  // Poll backend for assigned driver's position every 3 seconds
  useEffect(() => {
    if (!matchInfo?.driverID) return;

    const driverId = matchInfo.driverID;

    const fetchPosition = async () => {
      try {
        const response = await axios.post(
          "http://localhost:5001/driverPosition",
          { driver_id: driverId },
          { withCredentials: true }
        );

        const data = response.data;
        if (data.found && typeof data.latitude === "number" && typeof data.longitude === "number") {
          setDriverPosition([data.latitude, data.longitude]);
        }
      } catch (err) {
        console.error("Failed to fetch driver position", err);
      }
    };

    fetchPosition();
    const interval = setInterval(fetchPosition, 3000);

    return () => clearInterval(interval);
  }, [matchInfo?.driverID]);

  // Cancel match handler
  const handleCancelMatch = useCallback(async () => {
    try {
      await axios.post(
        "http://localhost:5001/cancelMatch",
        {},
        { withCredentials: true }
      );
      console.log("Match cancelled");
    } catch (err) {
      console.error("Failed to cancel match", err);
    }
    setShowCancelPrompt(false);
    router.push("/rider/booking");
  }, [router]);

  // Intercept browser back button
  useEffect(() => {
    if (matchInfo) return; // Already matched, no need to intercept

    const handlePopState = (e: PopStateEvent) => {
      // Push current state back so user stays on the page
      window.history.pushState(null, "", window.location.href);
      setShowCancelPrompt(true);
    };

    // Push an extra history entry so we can intercept back
    window.history.pushState(null, "", window.location.href);
    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [matchInfo]);

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
      {/* Cancel confirmation modal */}
      {showCancelPrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h2 className="text-lg font-semibold text-slate-100">Cancel driver search?</h2>
            <p className="mt-2 text-sm text-slate-400">
              Are you sure you want to stop searching for a driver? Your request will be removed from the queue.
            </p>
            <div className="mt-5 flex gap-3">
              <button
                onClick={() => setShowCancelPrompt(false)}
                className="flex-1 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
              >
                Keep searching
              </button>
              <button
                onClick={handleCancelMatch}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-red-600/30 transition hover:bg-red-500"
              >
                Yes, cancel
              </button>
            </div>
          </div>
        </div>
      )}

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
                : "We are finding a driver for your trip. This may take up to 15 seconds."}
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
