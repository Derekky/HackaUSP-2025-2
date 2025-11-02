import pyaudio
import numpy as np
from scipy import signal
import wave
import threading

class AudioFilter:
    def __init__(self, sample_rate=44100, chunk_size=512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.running = False
        
        # Design bandpass filter (250Hz to 2kHz)
        # We'll put a little bit of an offset so the annoying frequencies are less proeminent
        offset = 500.0
        self.lowcut = 200.0 + offset
        self.highcut = 1800.0 - offset
        self.nyquist = 0.5 * self.sample_rate
        
        # Create Butterworth bandpass filter with lower order for less latency
        low = self.lowcut / self.nyquist
        high = self.highcut / self.nyquist
        self.b, self.a = signal.butter(2, [low, high], btype='band')
        
        # Filter state for continuous filtering (reduces artifacts)
        self.zi = signal.lfilter_zi(self.b, self.a) * 0
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
    def list_audio_devices(self):
        """List all available audio devices"""
        print("\n=== Available Audio Devices ===")
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        input_devices = []
        output_devices = []
        
        for i in range(0, numdevices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append((i, device_info.get('name')))
                print(f"Input Device {i}: {device_info.get('name')}")
            if device_info.get('maxOutputChannels') > 0:
                output_devices.append((i, device_info.get('name')))
                print(f"Output Device {i}: {device_info.get('name')}")
        
        return input_devices, output_devices
        
    def apply_filter(self, audio_data):
        """Apply bandpass filter to audio data with stateful filtering"""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # Apply filter with state to maintain continuity between chunks
        filtered, self.zi = signal.lfilter(self.b, self.a, audio_array, zi=self.zi)

        
        # Normalize and convert back to int16
        filtered = np.clip(filtered, -32768, 32767)
        filtered = np.int16(filtered)
        
        return filtered.tobytes()
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for real-time audio processing"""
        if status:
            print(f"Status: {status}")
        
        # Apply filter to incoming audio
        filtered_data = self.apply_filter(in_data)
        
        return (filtered_data, pyaudio.paContinue)
    
    def start_realtime_filtering(self, input_device=None, output_device=None):
        """Start real-time audio filtering in continuous mode"""
        self.running = True
        
        print(f"\n{'='*60}")
        print(f"Real-time Audio Filter Active")
        print(f"Filtering OUT frequencies below {self.lowcut}Hz and above {self.highcut}Hz")
        print(f"Sample Rate: {self.sample_rate}Hz | Chunk Size: {self.chunk_size}")
        print(f"{'='*60}\n")
        
        # Reset filter state
        self.zi = signal.lfilter_zi(self.b, self.a) * 0
        
        # Open input stream (captures system audio or microphone)
        stream_in = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=self.chunk_size
        )
        
        # Open output stream (plays to speakers)
        stream_out = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True,
            output_device_index=output_device,
            frames_per_buffer=self.chunk_size
        )
        
        print("✓ Filtering started. Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                # Read audio data from input
                data = stream_in.read(self.chunk_size, exception_on_overflow=False)
                
                # Apply filter
                filtered_data = self.apply_filter(data)
                
                # Output filtered audio to speakers
                stream_out.write(filtered_data)
                
        except KeyboardInterrupt:
            print("\n\nStopping real-time filter...")
        
        finally:
            # Clean up streams
            stream_in.stop_stream()
            stream_in.close()
            stream_out.stop_stream()
            stream_out.close()
            self.running = False
            print("✓ Filter stopped.\n")
    
    def save_to_file(self, frames, filename="filtered_audio.wav"):
        """Save filtered audio to WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"Saved to {filename}")
    
    def close(self):
        """Clean up PyAudio"""
        self.p.terminate()


if __name__ == "__main__":
    # Create filter instance with smaller chunk for lower latency
    audio_filter = AudioFilter(sample_rate=44100, chunk_size=512)
    
    # List available audio devices
    input_devices, output_devices = audio_filter.list_audio_devices()
    
    print("\n" + "="*60)
    print("REAL-TIME AUDIO PROTECTION FILTER")
    print("="*60)
    print("This filter will block harmful frequencies:")
    print(f"  - Below {audio_filter.lowcut}Hz (infrasound)")
    print(f"  - Above {audio_filter.highcut}Hz (ultrasound)")
    print("="*60 + "\n")
    
    # Prompt for device selection (optional)
    print("Press Enter to use default devices, or specify device indices:")
    
    input_choice = input("Input device index (or press Enter for default): ").strip()
    output_choice = input("Output device index (or press Enter for default): ").strip()
    
    input_dev = int(input_choice) if input_choice else None
    output_dev = int(output_choice) if output_choice else None
    
    try:
        # Start real-time filtering (runs until Ctrl+C)
        audio_filter.start_realtime_filtering(
            input_device=input_dev, 
            output_device=output_dev
        )
    finally:
        # Clean up
        audio_filter.close()
        print("\n✓ Audio filter closed. Goodbye!\n")
