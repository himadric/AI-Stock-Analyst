import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';

export const revalidate = 3600; // Revalidate at most every hour

export async function GET() {
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
