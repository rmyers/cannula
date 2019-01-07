
export const flavorRam = (server) => {
  const flavor = server.flavor || {};
  return flavor.ram
}
