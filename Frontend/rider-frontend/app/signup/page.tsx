"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import "../globals.css";
/**
 * SignupPage
 *
 * Registration screen for new users.
 * This is a purely frontend implementation for now.
 * Backend integration (API calls, validation, etc.) can be added later.
 */
export default function SignupPage() {
  // Local component state for form fields.
  const [name, setName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [role, setRole] = useState("rider");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const router = useRouter();

  /**
   * Handle form submission.
   *
   * For now this only prevents the default browser refresh
   * and logs the form values. Replace this with a real
   * backend call when the API is ready.
   */
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Reset any previous error state and mark submission as in progress.
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      /**
       * Call the backend /signup route.
       *
       * The Flask backend expects the payload keys to be:
       *   - name
       *   - phone
       *   - role
       *   - password
       *
       * withCredentials: true ensures that the JWT cookie set by the
       * backend is stored in the browser.
       */
      await axios.post(
        "http://localhost:5001/signup",
        {
          name,
          phone: phoneNumber,
          role,
          password,
        },
        {
          withCredentials: true,
        },
      );

      // TODO: On success, navigate to a welcome or dashboard page.
      console.log("Signup successful");
      router.push("/login");
    } catch (error: any) {
      const apiMessage = error?.response?.data?.error;
      setErrorMessage(apiMessage || "Signup failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-500 via-slate-900 to-slate-900 px-4">
      <div className="w-full max-w-md bg-slate-950/80 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-md p-8">
        {/* Header section */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-semibold text-white tracking-tight">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-slate-200">
            Join the platform and start booking or fulfilling rides.
          </p>
        </div>

        {/* Signup form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label
              htmlFor="name"
              className="block text-sm font-medium text-slate-100"
            >
              Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter your full name"
              className="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 shadow-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="phoneNumber"
              className="block text-sm font-medium text-slate-100"
            >
              Phone number
            </label>
            <input
              id="phoneNumber"
              name="phoneNumber"
              type="tel"
              required
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              placeholder="Enter your phone number"
              className="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 shadow-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="role"
              className="block text-sm font-medium text-slate-100"
            >
              Role
            </label>
            <select
              id="role"
              name="role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 shadow-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
            >
              {/* Roles can be adjusted later depending on your business logic */}
              <option value="rider">Rider</option>
              <option value="driver">Driver</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-slate-100"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a strong password"
              className="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 shadow-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
            />
          </div>

          {/* Optional error message display */}
          {errorMessage && (
            <p className="text-xs text-red-400">{errorMessage}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-lg shadow-emerald-500/40 transition hover:bg-emerald-400 disabled:opacity-70 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
          >
            {isSubmitting ? "Signing up..." : "Sign up"}
          </button>
        </form>

        {/* Footer section with navigation to login */}
        <p className="mt-6 text-center text-xs text-slate-300">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-emerald-300 hover:text-emerald-200 underline-offset-4 hover:underline"
          >
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
