export default {
  name: "clock",
  key() {
    return "current";
  },
  async fetch() {
    return { iso: new Date().toISOString() };
  },
};
