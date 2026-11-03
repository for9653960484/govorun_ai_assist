import path from "path";
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

loadEnvConfig(path.resolve(process.cwd(), ".."));

const nextConfig: NextConfig = {
  serverExternalPackages: ["@prisma/client"],
};

export default nextConfig;
