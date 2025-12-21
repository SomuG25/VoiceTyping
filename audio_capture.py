"""
Audio capture module for Voice Typing application.
Uses PyAudio to capture microphone input in PCM 16-bit, 16kHz mono format.
"""

import asyncio
import threading
from typing import Callable, Optional, List, Dict, Any
import pyaudio

# Audio format constants (required by Gemini Live API)
RATE = 16000       # 16kHz sample rate
CHANNELS = 1       # Mono
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHUNK = 1024       # ~64ms per chunk at 16kHz


class AudioCapture:
    """Captures audio from microphone and streams it to a callback."""
    
    def __init__(self, device_index: Optional[int] = None):
        """
        Initialize audio capture.
        
        Args:
            device_index: Specific audio device index, or None for auto-detect
        """
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        
        # Smart device selection if not specified
        if device_index is None:
            self._initialize_pyaudio()
            best_device = self.get_default_device()
            if best_device:
                self._device_index = best_device['index']
                print(f"Auto-selected microphone: {best_device['name']}")
            else:
                self._device_index = None
                print("Warning: No microphone found, using system default")
        else:
            self._device_index = device_index
            
        self._is_recording = False
        self._audio_callback: Optional[Callable[[bytes], None]] = None
        self._record_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def _initialize_pyaudio(self) -> None:
        """Initialize PyAudio instance."""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
    
    def _cleanup_pyaudio(self) -> None:
        """Cleanup PyAudio resources."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available audio input devices.
        
        Returns:
            List of device info dictionaries with 'index', 'name', and 'channels'
        """
        self._initialize_pyaudio()
        devices = []
        
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Input device
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
        
        return devices
    
    def get_default_device(self) -> Optional[Dict[str, Any]]:
        """
        Get the best input device intelligently.
        Prioritizes built-in/Realtek mics over virtual devices.
        """
        self._initialize_pyaudio()
        try:
            # First, try Windows default
            try:
                default_info = self._pyaudio.get_default_input_device_info()
                default_name = default_info['name'].lower()
                
                # If default is NOT a virtual device, use it
                if not self._is_virtual_device(default_name):
                    return {
                        'index': default_info['index'],
                        'name': default_info['name'],
                        'channels': default_info['maxInputChannels'],
                        'sample_rate': int(default_info['defaultSampleRate'])
                    }
            except IOError:
                pass
            
            # If default is virtual, find best physical mic
            devices = self.list_devices()
            
            # Priority list (in order)
            priorities = [
                'realtek',      # Realtek built-in
                'microphone array',  # Generic array mic
                'internal',     # Internal mic
                'built-in',     # Built-in mic
                'microphone',   # Any mic
            ]
            
            # Try each priority
            for priority_term in priorities:
                for device in devices:
                    name_lower = device['name'].lower()
                    if priority_term in name_lower and not self._is_virtual_device(name_lower):
                        return device
            
            # Fallback: first non-virtual device
            for device in devices:
                if not self._is_virtual_device(device['name'].lower()):
                    return device
             
            # Last resort: any device
            return devices[0] if devices else None
                
        except Exception as e:
            print(f"Error detecting microphone: {e}")
            return None
    
    def _is_virtual_device(self, device_name: str) -> bool:
        """
        Check if a device is virtual (not a real microphone).
        
        Args:
            device_name: Device name in lowercase
            
        Returns:
            True if virtual, False if physical
        """
        virtual_keywords = [
            'droidcam',
            'virtual',
            'loopback',
            'stereo mix',
            'what u hear',
            'wave out mix',
            'cable output',
            'voicemeeter',
            'obs virtual',
            'snapcam',
        ]
        
        return any(keyword in device_name for keyword in virtual_keywords)
    
    def _record_loop(self) -> None:
        """Recording loop that runs in a separate thread."""
        try:
            self._initialize_pyaudio()
            
            # Open audio stream
            self._stream = self._pyaudio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=CHUNK
            )
            
            self._is_recording = True
            
            while not self._stop_event.is_set():
                try:
                    # Read audio data
                    data = self._stream.read(CHUNK, exception_on_overflow=False)
                    
                    # Send to callback if set
                    if self._audio_callback and data:
                        self._audio_callback(data)
                        
                except IOError as e:
                    print(f"Audio read error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Audio capture error: {e}")
        finally:
            self._is_recording = False
            self._cleanup_pyaudio()
    
    def start(self, callback: Callable[[bytes], None]) -> bool:
        """
        Start recording audio.
        
        Args:
            callback: Function to call with each audio chunk (bytes)
            
        Returns:
            True if recording started successfully
        """
        if self._is_recording:
            return True
        
        self._audio_callback = callback
        self._stop_event.clear()
        
        # Start recording in a separate thread
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()
        
        # Wait a bit for the stream to start
        import time
        time.sleep(0.1)
        
        return self._is_recording
    
    def stop(self) -> None:
        """Stop recording audio."""
        self._stop_event.set()
        
        if self._record_thread:
            self._record_thread.join(timeout=2.0)
            self._record_thread = None
        
        self._is_recording = False
        self._audio_callback = None
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
        self._cleanup_pyaudio()


def test_audio():
    """Test function to verify audio capture works."""
    print("Testing audio capture...")
    
    capture = AudioCapture()
    
    # List devices
    print("\nAvailable input devices:")
    devices = capture.list_devices()
    for dev in devices:
        print(f"  [{dev['index']}] {dev['name']} ({dev['channels']} channels)")
    
    # Get default device
    default = capture.get_default_device()
    if default:
        print(f"\nDefault device: [{default['index']}] {default['name']}")
    else:
        print("\nNo default input device found!")
        return False
    
    # Test recording for 2 seconds
    print("\nRecording for 2 seconds...")
    chunks_received = []
    
    def on_audio(data: bytes):
        chunks_received.append(data)
    
    if capture.start(on_audio):
        import time
        time.sleep(2)
        capture.stop()
        
        total_bytes = sum(len(c) for c in chunks_received)
        print(f"Received {len(chunks_received)} chunks ({total_bytes} bytes)")
        print("Audio capture test: SUCCESS")
        return True
    else:
        print("Failed to start recording!")
        return False


if __name__ == "__main__":
    test_audio()
