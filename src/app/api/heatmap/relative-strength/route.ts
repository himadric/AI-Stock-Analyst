import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { auth } from '@/auth';

export async function GET() {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    const client = await clientPromise;
    const db = client.db("ai_stock_analyst");

    // Sort by Market Cap descending usually, or just fetch all
    const data = await db.collection("snp_heatmap_data")
      .find({})
      .sort({ market_cap: -1 })
      .toArray();

    // Map _id to string if needed, or just return data
    const formattedData = data.map(item => ({
      ...item,
      _id: item._id.toString()
    }));

    return NextResponse.json(formattedData);
  } catch (e) {
    console.error("Failed to fetch heatmap data:", e);
    return NextResponse.json({ error: "Failed to fetch data" }, { status: 500 });
  }
}
