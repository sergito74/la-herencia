import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">La Herencia</h1>
      <p className="mt-2 text-slate-600">Sistema administrativo — migración.</p>
      <ul className="mt-6 list-disc pl-6">
        <li>
          <Link className="text-blue-700 underline" href="/compras">
            Compras
          </Link>
        </li>
      </ul>
    </main>
  );
}
