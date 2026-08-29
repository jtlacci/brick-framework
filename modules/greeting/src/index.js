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
  const clock = await adapters.clock();
  return {
    message: `Good ${periodFor(clock.iso)}, ${input.name.trim()}!`,
  };
}
