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
 * When a rider is matched:
 *   - Shows passenger info (name, phone, pickup station)
 *   - Provides an OTP entry field + "Start Trip" button
 *   - On submit, verifies OTP via /startTrip and updates trip to OnGoing
 */
export default function DriverReadyPage() {
  const router = useRouter();
  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [position, setPosition] = useState<LatLngExpression | null>(null);
  const [passengerInfo, setPassengerInfo] = useState<{
    name: string;
    phone: string;
    tripId: string;
  } | null>(null);
  const [riderPosition, setRiderPosition] = useState<LatLngExpression | null>(null);

  // OTP entry state
  const [otpInput, setOtpInput] = useState("");
  const [otpError, setOtpError] = useState<string | null>(null);
  const [tripStarted, setTripStarted] = useState(false);
  const [isStarting, setIsStarting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  // Basic auth guard using /me
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

  // Open WebSocket for driver location streaming
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

  // Open WebSocket for driver notifications (Redis Pub/Sub)
  useEffect(() => {
    if (!userId || !role) return;

    const notifWs = new WebSocket(`ws://localhost:5001/ws/driver/notifications/${userId}`);

    notifWs.onopen = () => {
      console.log("Notification WebSocket connected");
    };

    notifWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Notification WS received:", data);

        if (data.rider_name) {
          setPassengerInfo({
            name: data.rider_name || "",
            phone: data.rider_phone || "",
            tripId: data.trip_id || "",
          });
          // Reset OTP state on new assignment
          setOtpInput("");
          setOtpError(null);
          setTripStarted(false);
        }

        if (data.station_lat !== undefined && data.station_lon !== undefined) {
          setRiderPosition([data.station_lat, data.station_lon]);
        }
      } catch (e) {
        console.error("Failed to parse notification message", e);
      }
    };

    notifWs.onclose = () => {
      console.log("Notification WebSocket disconnected");
    };

    return () => {
      notifWs.close();
    };
  }, [userId, role]);

  const lastKnownRef = useRef<GeolocationPosition | null>(null);

  // Watch GPS and update position ref
  useEffect(() => {
    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        lastKnownRef.current = pos;
      },
      (err) => {
        console.error("Geolocation error", { code: err.code, message: err.message });
      },
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

  // Stream location over WebSocket whenever position changes
  useEffect(() => {
    if (!position || !userId || !role) return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    try {
      const [lat, lng] = position as [number, number];
      ws.send(JSON.stringify({ userId, role, lat, lng }));
    } catch (err) {
      console.error("Failed to send location over WebSocket", err);
    }
  }, [position, userId, role]);

  // Start trip: verify OTP and update status to OnGoing
  const handleStartTrip = async () => {
    if (!passengerInfo?.tripId) {
      setOtpError("No trip assigned yet.");
      return;
    }
    if (!otpInput.trim()) {
      setOtpError("Please enter the OTP.");
      return;
    }

    setIsStarting(true);
    setOtpError(null);

    try {
      await axios.post(
        "http://localhost:5001/startTrip",
        { trip_id: passengerInfo.tripId, otp: otpInput.trim() },
        { withCredentials: true }
      );
      // Trip is now OnGoing — navigate to the dedicated active trip screen
      router.push("/driver/onGoing");
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Failed to start trip. Please try again.";
      setOtpError(detail);
    } finally {
      setIsStarting(false);
    }
  };

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
        {/* Header */}
        <section className="relative z-10 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/85 px-5 py-4 shadow-lg shadow-black/40 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <p className="text-xs uppercase tracking-[0.25em] text-sky-300/80">
              Driver status
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              {passengerInfo ? "Passenger assigned" : "Searching for riders"}
            </h1>
            <p className="mt-2 max-w-xl text-xs text-slate-300">
              {passengerInfo
                ? "A passenger has been matched to you. Enter their OTP to start the trip."
                : "You are online and visible to riders in your area."}
            </p>

            {/* Passenger info card */}
            {passengerInfo && (
              <div className="mt-4 rounded-xl border border-sky-500/40 bg-sky-500/10 px-4 py-4 text-xs text-sky-50 shadow-md shadow-sky-500/20">
                <p className="text-[11px] uppercase tracking-[0.2em] text-sky-300/80">
                  Assigned passenger
                </p>
                <p className="mt-1 text-sm font-semibold">
                  {passengerInfo.name || "Unnamed passenger"}
                </p>
                <p className="mt-1 text-xs text-sky-100/90">
                  Contact: <span className="font-mono">{passengerInfo.phone}</span>
                </p>

                {/* OTP Entry or Success state */}
                {tripStarted ? (
                  <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-500/20 px-3 py-2 text-emerald-300">
                    <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    <span className="text-sm font-semibold">Trip started! Status: OnGoing</span>
                  </div>
                ) : (
                  <div className="mt-4 flex flex-col gap-2">
                    <label htmlFor="otp-input" className="text-[11px] uppercase tracking-[0.2em] text-sky-300/80">
                      Enter passenger OTP
                    </label>
                    <div className="flex gap-2">
                      <input
                        id="otp-input"
                        type="text"
                        inputMode="numeric"
                        maxLength={4}
                        value={otpInput}
                        onChange={(e) => {
                          setOtpInput(e.target.value.replace(/\D/g, ""));
                          setOtpError(null);
                        }}
                        placeholder="- - - -"
                        className="w-28 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-center font-mono text-lg tracking-[0.3em] text-slate-100 placeholder-slate-500 outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400/40"
                      />
                      <button
                        id="start-trip-btn"
                        onClick={handleStartTrip}
                        disabled={isStarting || otpInput.length < 4}
                        className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-sky-500/30 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isStarting && (
                          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        )}
                        Start Trip
                      </button>
                    </div>
                    {otpError && (
                      <p className="text-xs text-red-400">{otpError}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Status indicator */}
          {!passengerInfo && (
            <div className="flex items-center gap-3 text-xs text-slate-200">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
              <span>Waiting for trip requests</span>
            </div>
          )}
        </section>

        {/* Map section */}
        <section className="relative mt-6 flex-1 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80">
          {/* Placeholder background for the map */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#0ea5e9_0,_transparent_45%),_radial-gradient(circle_at_bottom,_#22c55e_0,_transparent_45%)] opacity-40" />

          {/* Live driver map */}
          <div className="relative z-10 h-full w-full">
            {position && (
              <DriverLiveMap
                position={position}
                riderPosition={riderPosition}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
