import { bridgeCall } from '../bridge';

export type ImageSource = 'camera' | 'gallery';

export type PickImageResult = {
  path: string;
};

export async function pickImageWithSource(source: ImageSource): Promise<PickImageResult> {
  const res = (await bridgeCall('pickImage', { source })) as { path?: string };
  const path = String(res?.path || '').trim();
  if (!path) {
    throw Object.assign(new Error('PICK_EMPTY'), { bridgeCode: -1 });
  }
  return { path };
}
