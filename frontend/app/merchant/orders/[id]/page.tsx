import { MerchantOrderDetailPage } from "../../../../components/merchant-pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MerchantOrderDetailPage orderId={Number(id)} />;
}
