"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import "../../globals.css";

interface Station {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

const STATIONS: Station[] = [
  { id: "1", name: "Central Hub Station", lat: 12.88005258237233, lon: 77.58702374463442 },
  { id: "2", name: "South Gateway Station", lat: 12.9352, lon: 77.6245 },
  { id: "3", name: "East Vista Station", lat: 12.9084, lon: 77.6753 },
  { id: "4", name: "Lakeside Terminal", lat: 12.8816, lon: 77.7261 },
];

export default function RiderBookingPage() {
  const router = useRouter();

  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  const [selectedStationId, setSelectedStationId] = useState<string>(STATIONS[0].id);
  const [destination, setDestination] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId || role !== "rider") return;

    setSubmitting(true);
    const station = STATIONS.find((s) => s.id === selectedStationId);
    if (!station) {
      setSubmitting(false);
      return;
    }

    const trimmedDestination = destination.trim();
    if (!trimmedDestination) {
      setSubmitting(false);
      return;
    }

    const destinationParam = trimmedDestination.replace(/\s+/g, "+");
    router.push(`/rider/booking/${station.id}/${destinationParam}/match`);
  };

  if (isLoadingUser) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm">Loading your rider profile...</p>
      </div>
    );
  }

  if (!userId || role !== "rider") {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <main className="relative mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 py-10 md:px-8">
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-950/85 px-6 py-5 shadow-lg shadow-black/40">
          <p className="text-xs uppercase tracking-[0.25em] text-emerald-300/80">
            Rider booking
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
            Book a ride to a station
          </h1>
          <p className="mt-2 max-w-xl text-xs text-slate-300">
            Choose the station you want to travel to. This page currently collects
            your choice; hooking it to the backend booking API can be done next.
          </p>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-6 shadow-lg shadow-black/40">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-[0.18em] text-slate-300">
                Start station
              </label>
              <select
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={selectedStationId}
                onChange={(e) => setSelectedStationId(e.target.value)}
              >
                {STATIONS.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.name}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-400">
                Station IDs are 1–4, with the same latitude and longitude as defined
                in the backend Station service.
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-[0.18em] text-slate-300">
                Destination address
              </label>
              <input
                type="text"
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                placeholder="Enter your destination (e.g. 123 MG Road)"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
              />
              <p className="text-[11px] text-slate-400">
                This address will be passed in the URL as a "+" separated parameter for
                the matching page.
              </p>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center justify-center rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-slate-950 shadow-md shadow-emerald-500/40 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-emerald-700"
            >
              {submitting ? "Submitting..." : "Confirm booking"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
