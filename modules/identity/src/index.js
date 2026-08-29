export async function execute({ input }) {
  if (typeof input?.name !== "string" || input.name.trim() === "") {
    throw new Error("name must be a non-empty string");
  }
  return { name: input.name.trim() };
}
