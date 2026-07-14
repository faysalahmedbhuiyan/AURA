/**
 * AURA Frontend — Voice Button.
 *
 * File: src/components/Voice/VoiceButton.jsx
 * Purpose: Push-to-talk microphone button for the chat input. Records
 *          audio, sends it to the existing /voice/transcribe endpoint
 *          (Phase 4), and hands the transcript to the chat send handler.
 *
 * Scope note: This implements push-to-talk reliably. Always-listening
 * mode with wake-word detection requires a persistent audio stream and
 * is left as a documented follow-up (see PHASE_REPORT.md) — browser
 * mic access without user interaction is also restricted by browsers,
 * making true always-on listening from a web/Electron renderer
 * non-trivial without additional native integration.
 */

import { useState, useRef } from 'react'
import { transcribeAudio } from '../../services/api'
import './VoiceButton.css'

export default function VoiceButton ({ onTranscript, disabled }) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = e => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setProcessing(true)
        try {
          const file = new File([blob], 'voice.webm', { type: 'audio/webm' })
          const result = await transcribeAudio(file)
          if (result.text) {
            onTranscript(result.text)
          }
        } catch (err) {
          console.error('Transcription failed:', err)
        } finally {
          setProcessing(false)
        }
      }

      recorder.start()
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (err) {
      console.error('Microphone access failed:', err)
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  return (
    <button
      type='button'
      className={`voice-button ${recording ? 'voice-button--recording' : ''}`}
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
      onMouseLeave={() => recording && stopRecording()}
      disabled={disabled || processing}
      title='Hold to speak'
    >
      {processing ? '⏳' : recording ? '🔴' : '🎤'}
    </button>
  )
}
