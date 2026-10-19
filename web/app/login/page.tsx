export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { error } = await searchParams;
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="mb-6 text-2xl font-semibold">StoryPulls</h1>
      <form action="/api/login" method="post" className="space-y-3">
        <input
          type="password"
          name="password"
          placeholder="Password"
          autoFocus
          className="w-full rounded-lg border border-line bg-transparent px-3 py-2 outline-none focus:border-accent"
        />
        {error && <p className="text-sm text-red-600">Wrong password.</p>}
        <button className="w-full rounded-lg bg-accent px-3 py-2 font-medium text-white">Sign in</button>
      </form>
    </main>
  );
}
