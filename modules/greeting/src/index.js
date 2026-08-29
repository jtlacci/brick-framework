function periodFor(iso) {
  const hour = new Date(iso).getUTCHours();
  if (hour < 12) return "morning";
  if (hour < 18) return "afternoon";
  return "evening";
}

export async function execute({ input, adapters }) {
  if (typeof input?.name !== "string" || input.name.trim() === "") {
    throw new Error("name must be a non-empty string");
  }
  const [clock, identity] = await Promise.all([
    adapters.clock(),
    adapters.identity({ name: input.name }),
  ]);
  return {
    message: `Good ${periodFor(clock.iso)}, ${identity.result.name}!`,
  };
}
