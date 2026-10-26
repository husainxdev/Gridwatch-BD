export type DemoArea = {
  id: string;
  name_bn: string;
  description: string;
  updated_at: string;
  power_status: "unknown";
};
export async function fetchAreas(signal: AbortSignal): Promise<DemoArea[]> {
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE_URL || ""}/api/demo/areas`,
    { signal },
  );
  if (!response.ok)
    throw new Error(
      "এলাকার তথ্য লোড করা যায়নি। ব্যাকএন্ড চালু আছে কি না দেখুন।",
    );
  const data = await response.json();
  if (data.data_mode !== "demonstration" || !Array.isArray(data.items))
    throw new Error("তথ্যের ধরন সঠিক নয়।");
  return data.items;
}
export function formatTime(value: string) {
  return new Intl.DateTimeFormat("bn-BD", {
    timeZone: "Asia/Dhaka",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
