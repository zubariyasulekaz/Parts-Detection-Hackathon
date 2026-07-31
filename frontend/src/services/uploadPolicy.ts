/**
 * Mirrors `Settings.MAX_UPLOAD_SIZE_MB` / `ALLOWED_IMAGE_EXTENSIONS` in
 * `partpilot/backend/config/settings.py`. Kept in sync manually — the
 * frontend can't import Python constants — so update both sides together.
 */
export const MAX_UPLOAD_SIZE_MB = 10
export const ALLOWED_IMAGE_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']

export interface FileValidationResult {
  valid: boolean
  error?: string
}

export function validateImageFile(file: File): FileValidationResult {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const typeAllowed = ALLOWED_IMAGE_MIME_TYPES.includes(file.type) || ALLOWED_IMAGE_EXTENSIONS.includes(extension)

  if (!typeAllowed) {
    return { valid: false, error: 'Unsupported file type. Upload a JPG, PNG, or WEBP image.' }
  }

  const maxBytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
  if (file.size > maxBytes) {
    return { valid: false, error: `File is too large. Maximum size is ${MAX_UPLOAD_SIZE_MB} MB.` }
  }

  return { valid: true }
}
