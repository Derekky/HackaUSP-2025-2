import pyaudio

class AudioPassthrough:
    def __init__(self, sample_rate=44100, chunk_size=512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.running = False
        
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
    
    def start_passthrough(self, input_device=None, output_device=None):
        """Start real-time audio passthrough (no filtering)"""
        self.running = True
        
        print(f"\n{'='*60}")
        print(f"Audio Passthrough Active - NO FILTERING")
        print(f"Sample Rate: {self.sample_rate}Hz | Chunk Size: {self.chunk_size}")
        print(f"{'='*60}\n")
        
        # Open input stream (captures audio from VB-Cable Output)
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
        
        print("✓ Passthrough started. Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                # Read audio data from input
                data = stream_in.read(self.chunk_size, exception_on_overflow=False)
                
                # Filter goes here
                
                
                # Output directly to speakers (no filtering)
                stream_out.write(data)
        except KeyboardInterrupt:
            print("\n\nStopping passthrough...")
        
        finally:
            # Clean up streams
            stream_in.stop_stream()
            stream_in.close()
            stream_out.stop_stream()
            stream_out.close()
            self.running = False
            print("✓ Passthrough stopped.\n")
    
    def close(self):
        """Clean up PyAudio"""
        self.p.terminate()


if __name__ == "__main__":
    # Create passthrough instance
    audio_passthrough = AudioPassthrough(sample_rate=44100, chunk_size=512)
    
    # List available audio devices
    input_devices, output_devices = audio_passthrough.list_audio_devices()
    
    print("\n" + "="*60)
    print("AUDIO PASSTHROUGH TEST - NO FILTERING")
    print("="*60)
    print("This will route audio directly without any processing.")
    print("Use this to test if VB-Cable routing is working correctly.")
    print("="*60 + "\n")
    
    # Prompt for device selection
    print("Select your devices:")
    print("  Input: Should be 'CABLE Output' (VB-Cable)")
    print("  Output: Should be your physical speakers/headphones\n")
    
    input_choice = input("Input device index (or press Enter for default): ").strip()
    output_choice = input("Output device index (or press Enter for default): ").strip()
    
    input_dev = int(input_choice) if input_choice else None
    output_dev = int(output_choice) if output_choice else None
    
    try:
        # Start passthrough (runs until Ctrl+C)
        audio_passthrough.start_passthrough(
            input_device=input_dev, 
            output_device=output_dev
        )
    finally:
        # Clean up
        audio_passthrough.close()
        print("\n✓ Passthrough closed. Goodbye!\n")
