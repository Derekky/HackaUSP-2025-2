import customtkinter as ctk
import pyaudio
import numpy as np
from scipy import signal
import threading
from datetime import datetime

class AudioProcessor:
    """Handles both passthrough and filtering audio processing"""
    def __init__(self, sample_rate=44100, chunk_size=512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.running = False
        self.mode = None  # 'passthrough' or 'filter'
        
        # Filter design
        self.lowcut = 700.0
        self.highcut = 1300.0
        self.nyquist = 0.5 * self.sample_rate
        
        self.update_filter()
        
        self.p = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.processing_thread = None
    
    def update_filter(self):
        """Update filter coefficients based on current cutoff frequencies"""
        low = self.lowcut / self.nyquist
        high = self.highcut / self.nyquist
        self.b, self.a = signal.butter(3, [low, high], btype='band')
        self.zi = signal.lfilter_zi(self.b, self.a) * 0
        
    def get_devices(self):
        """Get list of available audio devices"""
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        input_devices = []
        output_devices = []
        
        for i in range(0, numdevices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append((i, device_info.get('name')))
            if device_info.get('maxOutputChannels') > 0:
                output_devices.append((i, device_info.get('name')))
        
        return input_devices, output_devices
    
    def apply_filter(self, audio_data):
        """Apply bandpass filter to audio data"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        filtered, self.zi = signal.lfilter(self.b, self.a, audio_array, zi=self.zi)
        filtered = np.clip(filtered, -32768, 32767)
        filtered = np.int16(filtered)
        return filtered.tobytes()
    
    def process_audio(self, input_device, output_device, mode, log_callback):
        """Main audio processing loop"""
        self.mode = mode
        self.running = True
        
        # Reset filter state
        self.update_filter()
        
        try:
            # Open streams
            self.stream_in = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=self.chunk_size
            )
            
            self.stream_out = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                output_device_index=output_device,
                frames_per_buffer=self.chunk_size
            )
            
            log_callback(f"✓ {mode.upper()} iniciado com sucesso")
            
            while self.running:
                data = self.stream_in.read(self.chunk_size, exception_on_overflow=False)
                
                if mode == 'filter':
                    processed_data = self.apply_filter(data)
                else:  # passthrough
                    processed_data = data
                
                self.stream_out.write(processed_data)
                
        except Exception as e:
            log_callback(f"✗ Erro: {str(e)}")
        finally:
            #self.close()
            log_callback(f"✓ {mode.upper()} parado")
    
    def start(self, input_device, output_device, mode, log_callback):
        """Start audio processing in a separate thread"""
        if self.running:
            return False
        
        self.processing_thread = threading.Thread(
            target=self.process_audio,
            args=(input_device, output_device, mode, log_callback),
            daemon=True
        )
        self.processing_thread.start()
        return True
    
    def stop(self):
        """Stop audio processing"""

        self.running = False

        if self.stream_in or self.stream_out:
            print("I remember")
            self.stream_in.stop_stream()
            self.stream_in.close()
            self.stream_in = None
        

        # if self.stream_out:
        #     print("You was conflicted")
        #     self.stream_out.stop_stream()
        #     self.stream_out.close()
        #     self.stream_out = None

    
    def close(self):
        """Clean up PyAudio"""
        print("bbbbbbbbbbbb")
        self.stop()
        print("Misusing your influence")
        #self.p.terminate()
        print("AAAAAAAAAAAAAAAAAAAAA")


class AudioFilterGUI:
    def __init__(self):
        # Set appearance and theme (high contrast for accessibility)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Protetor de Áudio - Filtro de Frequências")
        self.root.geometry("1400x750")
        
        # Audio processor
        self.processor = AudioProcessor()
        
        # Colors for accessibility (high contrast, colorblind-friendly)
        self.color_bg = "#1a1a1a"
        self.color_panel = "#2b2b2b"
        self.color_active = "#00b894"  # Green for active
        self.color_inactive = "#636e72"  # Gray for inactive
        self.color_warning = "#fdcb6e"  # Yellow for warnings
        self.color_error = "#d63031"  # Red for errors
        self.color_text = "#ffffff"
        
        self.status = "inactive"  # inactive, passthrough, filter
        
        self.setup_ui()
        self.load_devices()
        
    def setup_ui(self):
        """Create the user interface"""
        # Main horizontal container
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=2)
        self.root.grid_rowconfigure(0, weight=1)
        
        # ===== LEFT PANEL: Device Selection =====
        left_panel = ctk.CTkFrame(self.root, corner_radius=15)
        left_panel.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        ctk.CTkLabel(
            left_panel, 
            text="🎛️ DISPOSITIVOS", 
            font=("Arial Bold", 24),
            text_color=self.color_text
        ).pack(pady=(15, 20))
        
        # Input device
        ctk.CTkLabel(
            left_panel, 
            text="Entrada (VB-Cable Output):", 
            font=("Arial", 16),
            text_color=self.color_text
        ).pack(pady=(5, 3))
        
        self.input_device_var = ctk.StringVar(value="Selecione...")
        self.input_dropdown = ctk.CTkComboBox(
            left_panel,
            variable=self.input_device_var,
            font=("Arial", 16),
            height=40,
            width=350,
            state="readonly"
        )
        self.input_dropdown.pack(pady=(0, 15))
        
        # Output device
        ctk.CTkLabel(
            left_panel, 
            text="Saída (Seus Alto-falantes):", 
            font=("Arial", 16),
            text_color=self.color_text
        ).pack(pady=(5, 3))
        
        self.output_device_var = ctk.StringVar(value="Selecione...")
        self.output_dropdown = ctk.CTkComboBox(
            left_panel,
            variable=self.output_device_var,
            font=("Arial", 16),
            height=40,
            width=350,
            state="readonly"
        )
        self.output_dropdown.pack(pady=(0, 15))
        
        # Refresh button
        ctk.CTkButton(
            left_panel,
            text="🔄 Atualizar Dispositivos",
            font=("Arial Bold", 15),
            height=40,
            width=280,
            command=self.load_devices,
            fg_color=self.color_warning,
            hover_color="#e17055"
        ).pack(pady=15)
        
        # Filter configuration
        ctk.CTkLabel(
            left_panel, 
            text="⚙️ Configuração do Filtro", 
            font=("Arial Bold", 18),
            text_color=self.color_text
        ).pack(pady=(20, 10))
        
        # Low frequency input
        ctk.CTkLabel(
            left_panel, 
            text="Frequência Baixa (Hz):", 
            font=("Arial", 14),
            text_color=self.color_text
        ).pack(pady=(5, 3))
        
        self.lowcut_entry = ctk.CTkEntry(
            left_panel,
            font=("Arial", 16),
            height=38,
            width=200,
            justify="center"
        )
        self.lowcut_entry.insert(0, str(int(self.processor.lowcut)))
        self.lowcut_entry.pack(pady=(0, 8))
        
        # High frequency input
        ctk.CTkLabel(
            left_panel, 
            text="Frequência Alta (Hz):", 
            font=("Arial", 14),
            text_color=self.color_text
        ).pack(pady=(5, 3))
        
        self.highcut_entry = ctk.CTkEntry(
            left_panel,
            font=("Arial", 16),
            height=38,
            width=200,
            justify="center"
        )
        self.highcut_entry.insert(0, str(int(self.processor.highcut)))
        self.highcut_entry.pack(pady=(0, 8))
        
        # Apply filter button
        ctk.CTkButton(
            left_panel,
            text="✓ Aplicar Frequências",
            font=("Arial Bold", 14),
            height=38,
            width=200,
            command=self.apply_frequencies,
            fg_color=self.color_active,
            hover_color="#55efc4"
        ).pack(pady=(8, 10))
        
        # ===== CENTER PANEL: Controls =====
        center_panel = ctk.CTkFrame(self.root, corner_radius=15)
        center_panel.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        
        ctk.CTkLabel(
            center_panel, 
            text="🎚️ CONTROLES", 
            font=("Arial Bold", 28),
            text_color=self.color_text
        ).pack(pady=(20, 40))
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            center_panel,
            text="● INATIVO",
            font=("Arial Bold", 32),
            text_color=self.color_inactive,
            width=300,
            height=80
        )
        self.status_label.pack(pady=40)
        
        # Passthrough toggle button
        self.passthrough_btn = ctk.CTkButton(
            center_panel,
            text="▶ INICIAR PASSTHROUGH\n(Sem Filtro)",
            font=("Arial Bold", 24),
            height=130,
            width=380,
            command=self.toggle_passthrough,
            fg_color="#0984e3",
            hover_color="#74b9ff"
        )
        self.passthrough_btn.pack(pady=35)
        
        # Filter toggle button
        self.filter_btn = ctk.CTkButton(
            center_panel,
            text="▶ INICIAR FILTRO\n(Proteção Ativa)",
            font=("Arial Bold", 24),
            height=130,
            width=380,
            command=self.toggle_filter,
            fg_color=self.color_active,
            hover_color="#55efc4"
        )
        self.filter_btn.pack(pady=35)
        
        # ===== RIGHT PANEL: Log =====
        right_panel = ctk.CTkFrame(self.root, corner_radius=15)
        right_panel.grid(row=0, column=2, padx=15, pady=15, sticky="nsew")
        
        ctk.CTkLabel(
            right_panel, 
            text="📋 LOG DE ATIVIDADES", 
            font=("Arial Bold", 28),
            text_color=self.color_text
        ).pack(pady=(20, 20))
        
        # Log text box
        self.log_text = ctk.CTkTextbox(
            right_panel,
            font=("Consolas", 16),
            width=500,
            height=550,
            wrap="word"
        )
        self.log_text.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        
        # Clear log button
        ctk.CTkButton(
            right_panel,
            text="🗑️ Limpar Log",
            font=("Arial", 16),
            height=40,
            command=self.clear_log,
            fg_color=self.color_inactive,
            hover_color="#95a5a6"
        ).pack(pady=(0, 20))
        
        self.add_log("Sistema iniciado. Selecione os dispositivos de áudio.")
    
    def load_devices(self):
        """Load available audio devices"""
        try:
            input_devices, output_devices = self.processor.get_devices()
            
            # Update dropdowns
            input_names = [f"{idx}: {name}" for idx, name in input_devices]
            output_names = [f"{idx}: {name}" for idx, name in output_devices]
            
            self.input_dropdown.configure(values=input_names)
            self.output_dropdown.configure(values=output_names)
            
            if input_names:
                self.input_dropdown.set(input_names[0])
            if output_names:
                self.output_dropdown.set(output_names[0])
            
            self.add_log(f"✓ {len(input_devices)} entradas e {len(output_devices)} saídas encontradas")
        except Exception as e:
            self.add_log(f"✗ Erro ao carregar dispositivos: {str(e)}")
    
    def add_log(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete("1.0", "end")
        self.add_log("Log limpo")
    
    def apply_frequencies(self):
        """Apply the frequency values from entry fields"""
        try:
            lowcut = float(self.lowcut_entry.get())
            highcut = float(self.highcut_entry.get())
            
            # Validation
            if lowcut <= 0 or highcut <= 0:
                self.add_log("✗ Erro: Frequências devem ser positivas")
                return
            
            if lowcut >= highcut:
                self.add_log("✗ Erro: Frequência baixa deve ser menor que a alta")
                return
            
            if highcut > self.processor.sample_rate / 2:
                self.add_log(f"✗ Erro: Frequência alta não pode exceder {self.processor.sample_rate/2:.0f} Hz")
                return
            
            # Update processor
            self.processor.lowcut = lowcut
            self.processor.highcut = highcut
            
            if not self.processor.running:
                self.processor.update_filter()
            
            self.add_log(f"✓ Filtro configurado: {lowcut:.0f} Hz - {highcut:.0f} Hz")
            
        except ValueError:
            self.add_log("✗ Erro: Digite valores numéricos válidos")
    
    def get_selected_devices(self):
        """Get selected device indices"""
        try:
            input_str = self.input_device_var.get()
            output_str = self.output_device_var.get()
            
            input_idx = int(input_str.split(":")[0]) if ":" in input_str else None
            output_idx = int(output_str.split(":")[0]) if ":" in output_str else None
            
            return input_idx, output_idx
        except:
            return None, None
    
    def update_status(self, status_text, color):
        """Update status indicator"""
        self.status = status_text.lower()
        self.status_label.configure(text=f"● {status_text.upper()}", text_color=color)
    
    def toggle_passthrough(self):
        """Toggle passthrough mode on/off"""
        if self.processor.running:
            if self.processor.mode == 'passthrough':
                # Stop passthrough
                self.processor.close()
                self.reset_passthrough_button()
            else:
                self.add_log("⚠ Pare o filtro antes de iniciar o passthrough")
            return
        
        input_idx, output_idx = self.get_selected_devices()
        if input_idx is None or output_idx is None:
            self.add_log("✗ Selecione os dispositivos de entrada e saída")
            return
        
        success = self.processor.start(input_idx, output_idx, 'passthrough', self.add_log)
        if success:
            self.update_status("PASSTHROUGH ATIVO", "#0984e3")
            self.passthrough_btn.configure(
                text="⏹ PARAR PASSTHROUGH",
                fg_color=self.color_error,
                hover_color="#ff7675"
            )
            self.filter_btn.configure(state="disabled")
    
    def reset_passthrough_button(self):
        """Reset passthrough button to initial state"""
        self.update_status("INATIVO", self.color_inactive)
        self.passthrough_btn.configure(
            text="▶ INICIAR PASSTHROUGH\n(Sem Filtro)",
            fg_color="#0984e3",
            hover_color="#74b9ff"
        )
        self.filter_btn.configure(state="normal")
        self.add_log("✓ Passthrough parado")
    
    def toggle_filter(self):
        """Toggle filter mode on/off"""
        if self.processor.running:
            if self.processor.mode == 'filter':
                # Stop filter
                self.reset_filter_button()
                self.processor.close()
                
            else:
                self.add_log("⚠ Pare o passthrough antes de iniciar o filtro")
            return
        
        input_idx, output_idx = self.get_selected_devices()
        if input_idx is None or output_idx is None:
            self.add_log("✗ Selecione os dispositivos de entrada e saída")
            return
        
        # Apply frequencies before starting
        self.apply_frequencies()
        
        success = self.processor.start(input_idx, output_idx, 'filter', self.add_log)
        if success:
            self.update_status("FILTRO ATIVO", self.color_active)
            self.filter_btn.configure(
                text="⏹ PARAR FILTRO",
                fg_color=self.color_error,
                hover_color="#ff7675"
            )
            self.passthrough_btn.configure(state="disabled")
    
    def reset_filter_button(self):
        """Reset filter button to initial state"""
        self.update_status("INATIVO", self.color_inactive)
        self.filter_btn.configure(
            text="▶ INICIAR FILTRO\n(Proteção Ativa)",
            fg_color=self.color_active,
            hover_color="#55efc4"
        )
        self.passthrough_btn.configure(state="normal")
        self.add_log("✓ Filtro parado")
    
    def on_closing(self):
        """Handle window close event"""
        self.processor.close()
        self.root.destroy()
    
    def run(self):
        """Start the GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


if __name__ == "__main__":
    app = AudioFilterGUI()
    app.run()
