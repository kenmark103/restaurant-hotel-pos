/**
 * shared/hooks/useBarcodeScanner.ts
 *
 * Uses the browser's native BarcodeDetector API (Chrome/Edge) or listens for
 * rapid keyboard input from a USB barcode scanner (all browsers).
 *
 * USB scanners act as keyboards — they type the barcode and then send Enter.
 * This hook captures that input when the page is focused, without needing
 * a visible input field.
 *
 * Usage:
 *   const { isListening, startListening, stopListening } = useBarcodeScanner({
 *     onScan: (barcode) => handleBarcode(barcode),
 *   })
 */

import { useCallback, useEffect, useRef, useState } from 'react'

interface UseBarcodeOptions {
  onScan: (barcode: string) => void
  /** Minimum barcode length to trigger onScan. Default: 3 */
  minLength?: number
  /** Max ms between keystrokes to be considered a scanner (not typing). Default: 50 */
  scannerDelay?: number
}

export function useBarcodeScanner({
  onScan,
  minLength = 3,
  scannerDelay = 50,
}: UseBarcodeOptions) {
  const [isListening, setIsListening] = useState(false)
  const bufferRef = useRef('')
  const lastKeyTimeRef = useRef(0)

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const now = Date.now()
      const timeDiff = now - lastKeyTimeRef.current
      lastKeyTimeRef.current = now

      // If too slow between keystrokes, reset buffer (human typing, not scanner)
      if (timeDiff > scannerDelay && bufferRef.current.length > 0) {
        bufferRef.current = ''
      }

      if (event.key === 'Enter') {
        const code = bufferRef.current.trim()
        bufferRef.current = ''
        if (code.length >= minLength) {
          onScan(code)
        }
        return
      }

      // Only capture printable single characters
      if (event.key.length === 1) {
        bufferRef.current += event.key
      }
    },
    [onScan, minLength, scannerDelay],
  )

  const startListening = useCallback(() => {
    setIsListening(true)
    bufferRef.current = ''
    window.addEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const stopListening = useCallback(() => {
    setIsListening(false)
    window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown])

  return { isListening, startListening, stopListening }
}