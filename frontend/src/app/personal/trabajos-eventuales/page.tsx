"use client";
import { Suspense } from "react";
import { TrabajosEventuales } from "@/components/trabajos-eventuales/TrabajosEventuales";
export default function Page() { return <Suspense fallback={<p className="p-8">Cargando…</p>}><TrabajosEventuales /></Suspense>; }
