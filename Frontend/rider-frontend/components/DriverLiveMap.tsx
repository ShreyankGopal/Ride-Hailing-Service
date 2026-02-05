"use client";

import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import { useEffect, useState } from "react";
import L, { type LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default marker icon issue in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

/** Forces Leaflet to recalc size after render */
function FixMapResize() {
  const map = useMap();

  useEffect(() => {
    setTimeout(() => {
      map.invalidateSize();
    }, 100);
  }, [map]);

  return null;
}

export default function DriverLiveMap({ position }: { position: LatLngExpression }) {

  // useEffect(() => {
  //   if (!navigator.geolocation) {
  //     console.error("Geolocation not supported");
  //     return;
  //   }

  //   const watchId = navigator.geolocation.watchPosition(
  //     (pos) => {
  //       setPosition([
  //         pos.coords.latitude,
  //         pos.coords.longitude,
  //       ]);
  //     },
  //     (err) => {
  //       console.error("GPS error:", err);
  //     },
  //     {
  //       enableHighAccuracy: true,
  //       maximumAge: 2000,
  //       timeout: 10000,
  //     }
  //   );

  //   return () => navigator.geolocation.clearWatch(watchId);
  // }, []);

  if (!position) {
    return (
      <div className="flex h-full min-h-[300px] items-center justify-center text-xs text-slate-300">
        Waiting for GPS signal…
      </div>
    );
  }

  return (
  <MapContainer
    center={position}
    zoom={15}
    scrollWheelZoom={true}
    style={{ height: "100%", width: "100%", minHeight: "500px" }}
    className="z-0"
  >
    <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    />
    <Marker position={position} />
    <FixMapResize />
  </MapContainer>
);
}
