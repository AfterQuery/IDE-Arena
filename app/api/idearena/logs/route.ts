import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

export async function GET() {
  try {
    const logsDir = path.join(process.cwd(), "logs");

    const files = await fs.readdir(logsDir);
    const logFiles = await Promise.all(
      files
        .filter((file) => file.endsWith(".log"))
        .map(async (file) => {
          const stats = await fs.stat(path.join(logsDir, file));
          return {
            filename: file,
            size: stats.size,
          };
        })
    );

    return NextResponse.json(logFiles);
  } catch (error: any) {
    console.error("Error reading logs directory:", error);
    return NextResponse.json(
      { error: "Failed to read logs", details: error.message },
      { status: 500 }
    );
  }
}
