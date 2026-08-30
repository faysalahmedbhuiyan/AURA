/**
 * AURA Frontend — Voice Button.
 *
 * File: src/components/Voice/VoiceButton.jsx
 * Purpose: Click-to-toggle microphone button (click to start recording,
 *          click again to stop). Push-to-talk via mousedown/mouseup was
 *          unreliable — a quick click fired mouseup almost immediately,
 *          producing near-empty audio and silent failures. Toggle mode
 *          guarantees a minimum recording duration and gives clear
 *          visual feedback throughout.
 */

import { useState, useRef } from 'react'
import { transcribeAudio } from '../../services/api'
import './VoiceButton.css'

const MIN_RECORDING_MS = 400 // guards against near-instant clicks producing empty audio

export default function VoiceButton ({
  onTranscript,
  disabled,
  language = 'en'
}) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [notice, setNotice] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const startTimeRef = useRef(0)

  const startRecording = async () => {
    setNotice(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      startTimeRef.current = Date.now()

      recorder.ondataavailable = e => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const elapsed = Date.now() - startTimeRef.current
        const totalBytes = chunksRef.current.reduce((n, c) => n + c.size, 0)

        if (elapsed < MIN_RECORDING_MS || totalBytes === 0) {
          setNotice('খুব ছোট রেকর্ডিং — আবার চেষ্টা করুন।')
          return
        }

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setProcessing(true)
        try {
          const file = new File([blob], 'voice.webm', { type: 'audio/webm' })
          const result = await transcribeAudio(file, language)
          if (result.text && result.text.trim()) {
            onTranscript(result.text.trim())
          } else {
            setNotice('কিছু শুনতে পাইনি — আবার বলুন।')
          }
        } catch (err) {
          console.error('Transcription failed:', err)
          setNotice('Transcription ব্যর্থ হয়েছে।')
        } finally {
          setProcessing(false)
        }
      }

      // timeslice=250 forces periodic ondataavailable events so we always
      // capture chunks even if stop() is called soon after start().
      recorder.start(250)
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (err) {
      console.error('Microphone access failed:', err)
      setNotice('মাইক্রোফোন অ্যাক্সেস করা যায়নি।')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const handleClick = () => {
    if (processing) return
    if (recording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <div className='voice-button-wrap'>
      <button
        type='button'
        className={`voice-button ${recording ? 'voice-button--recording' : ''}`}
        onClick={handleClick}
        disabled={disabled || processing}
        title={recording ? 'Click to stop' : 'Click to speak'}
      >
        {processing ? '⏳' : recording ? '🔴' : '🎤'}
      </button>
      {notice && <span className='voice-button__notice'>{notice}</span>}
    </div>
  )
}
