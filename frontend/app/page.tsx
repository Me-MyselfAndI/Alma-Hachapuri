export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold">Alma Lead Intake</h1>
      <p className="text-zinc-600">
        Public lead form and internal dashboard will live here. API:{" "}
        {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
      </p>
    </main>
  );
}
