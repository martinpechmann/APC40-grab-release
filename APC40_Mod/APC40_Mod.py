from __future__ import with_statement
from functools import partial
import Live
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ComboElement import ComboElement, MultiElement
from _Framework.ControlSurface import OptimizedControlSurface
from _Framework.Layer import Layer
from _Framework.M4LInterfaceComponent import M4LInterfaceComponent
from _Framework.ModesComponent import ModesComponent, ComponentMode, AddLayerMode, DelayMode, ImmediateBehaviour
from _Framework.Resource import PrioritizedResource
from _Framework.SessionRecordingComponent import SessionRecordingComponent
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.ClipCreator import ClipCreator
from _Framework.Util import recursive_map
from _Framework.Skin import merge_skins
from _APC.APC import APC
from _APC.DeviceBankButtonElement import DeviceBankButtonElement
from _APC.DetailViewCntrlComponent import DetailViewCntrlComponent
from _APC.ControlElementUtils import make_button, make_encoder, make_slider, make_ring_encoder, make_pedal_button
from _APC.SkinDefault import make_default_skin, make_biled_skin, make_stop_button_skin
from DeviceComponent import DeviceComponent
from MixerComponent import MixerComponent
from QuantizationComponent import QuantizationComponent
from SessionComponent import SessionComponent
from TransportComponent import TransportComponent
NUM_TRACKS = 8
NUM_SCENES = 5

class APC40_Mod(APC, OptimizedControlSurface):

    def __init__(self, *a, **k):
        super(APC40_Mod, self).__init__(*a, **k)
        self._color_skin = merge_skins(make_default_skin(), make_biled_skin())
        self._default_skin = make_default_skin()
        self._stop_button_skin = merge_skins(make_default_skin(), make_stop_button_skin())
        with self.component_guard():
            self._create_controls()
            self._create_session()
            self._create_mixer()
            self._create_transport()
            self._create_device()
            self._create_view_control()
            self._create_quantization_selection()
            self._init_track_modes()
            self._create_m4l_interface()
            self._session.set_mixer(self._mixer)
        self.set_highlighting_session_component(self._session)
        self.set_device_component(self._device)
        self._device_selection_follows_track_selection = True

    def _with_shift(self, button):
        return ComboElement(button, modifiers=[self._shift_button])

    def _create_controls(self):
        make_on_off_button = partial(make_button, skin=self._default_skin)
        make_color_button = partial(make_button, skin=self._color_skin)
        make_stop_button = partial(make_button, skin=self._stop_button_skin)

        self._shift_button = make_button(0, 98, name='Shift_Button', resource_type=PrioritizedResource)
        self._left_button = make_button(0, 97, name='Bank_Select_Left_Button')
        self._right_button = make_button(0, 96, name='Bank_Select_Right_Button')
        self._up_button = make_button(0, 94, name='Bank_Select_Up_Button')
        self._down_button = make_button(0, 95, name='Bank_Select_Down_Button')
        self._stop_buttons = ButtonMatrixElement(rows=[[ make_stop_button(track, 52, name='%d_Stop_Button' % track) for track in xrange(NUM_TRACKS) ]], name="Stop_Buttons")
        self._stop_all_button = make_button(0, 81, name='Stop_All_Clips_Button')
        self._scene_launch_buttons_raw = [ make_color_button(0, scene + 82, name='Scene_%d_Launch_Button' % scene) for scene in xrange(NUM_SCENES) ]
        self._scene_launch_buttons = ButtonMatrixElement(rows=[self._scene_launch_buttons_raw], name="Scene_Launch_Buttons")
        self._matrix_rows_raw = [ [ make_color_button(track, 53 + scene, name='%d_Clip_%d_Button' % (track, scene)) for track in xrange(NUM_TRACKS) ] for scene in xrange(NUM_SCENES) ]
        self._session_matrix = ButtonMatrixElement(rows=self._matrix_rows_raw, name='Button_Matrix')
        self._pan_button = make_on_off_button(0, 87, name='Pan_Button')
        self._send_a_button = make_on_off_button(0, 88, name='Send_A_Button')
        self._send_b_button = make_on_off_button(0, 89, name='Send_B_Button')
        self._send_c_button = make_on_off_button(0, 90, name='Send_C_Button')
        self._mixer_encoders = ButtonMatrixElement(rows=[[ make_ring_encoder(48 + track, 56 + track, name='Track_Control_%d' % track) for track in xrange(NUM_TRACKS) ]], name="Track_Controls")
        self._volume_controls = ButtonMatrixElement(rows=[[ make_slider(track, 7, name='%d_Volume_Control' % track) for track in xrange(NUM_TRACKS) ]])
        self._master_volume_control = make_slider(0, 14, name='Master_Volume_Control')
        self._prehear_control = make_encoder(0, 47, name='Prehear_Volume_Control')
        self._crossfader_control = make_slider(0, 15, name='Crossfader')
        self._raw_select_buttons = [ make_on_off_button(channel, 51, name='%d_Select_Button' % channel) for channel in xrange(NUM_TRACKS) ]
        self._arm_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 48, name='%d_Arm_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Arm_Buttons")
        self._solo_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 49, name='%d_Solo_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Solo_Buttons")
        self._mute_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 50, name='%d_Mute_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Mute_Buttons")
        self._select_buttons = ButtonMatrixElement(rows=[self._raw_select_buttons], name="Select_Buttons")
        self._master_select_button = make_on_off_button(channel=0, identifier=80, name='Master_Select_Button')
        self._quantization_buttons = ButtonMatrixElement(rows=[[ ComboElement(button, modifiers=[self._shift_button]) for button in self._raw_select_buttons ]], name="Quantization_Buttons")
        self._play_button = make_on_off_button(0, 91, name='Play_Button')
        self._stop_button = make_on_off_button(0, 92, name='Stop_Button')
        self._record_button = make_on_off_button(0, 93, name='Record_Button')
        self._nudge_down_button = make_button(0, 101, name='Nudge_Down_Button')
        self._nudge_up_button = make_button(0, 100, name='Nudge_Up_Button')
        self._tap_tempo_button = make_button(0, 99, name='Tap_Tempo_Button')
        self._device_controls = ButtonMatrixElement(rows=[[ make_ring_encoder(16 + index, 24 + index, name='Device_Control_%d' % index) for index in xrange(8) ]], name="Device_Controls")
        self._device_control_buttons_raw = [ make_on_off_button(0, 58 + index) for index in xrange(8) ]
        self._device_bank_buttons = ButtonMatrixElement(rows=[[ DeviceBankButtonElement(button, modifiers=[self._shift_button]) for button in self._device_control_buttons_raw ]], name="Device_Bank_Buttons")
        self._device_clip_toggle_button = self._device_control_buttons_raw[0]
        self._device_clip_toggle_button.name = 'Clip_Device_Button'
        self._device_on_off_button = self._device_control_buttons_raw[1]
        self._device_on_off_button.name = 'Device_On_Off_Button'
        self._detail_left_button = self._device_control_buttons_raw[2]
        self._detail_left_button.name = 'Prev_Device_Button'
        self._detail_right_button = self._device_control_buttons_raw[3]
        self._detail_right_button.name = 'Next_Device_Button'
        self._detail_toggle_button = self._device_control_buttons_raw[4]
        self._detail_toggle_button.name = 'Detail_View_Button'
        self._rec_quantization_button = self._device_control_buttons_raw[5]
        self._rec_quantization_button.name ='Rec_Quantization_Button'
        self._overdub_button = self._device_control_buttons_raw[6]
        self._overdub_button.name = 'Overdub_Button'
        self._metronome_button = self._device_control_buttons_raw[7]
        self._metronome_button.name = 'Metronome_Button'
        self._selected_slot_launch_button = make_pedal_button(67, name='Selected_Slot_Launch_Button')
        self._selected_scene_launch_button = make_pedal_button(64, name='Selected_Scene_Launch_Button')
        self._shifted_matrix = ButtonMatrixElement(rows=recursive_map(self._with_shift, self._matrix_rows_raw), name="Shifted_Matrix")
        self._shifted_scene_buttons = ButtonMatrixElement(rows=[[ self._with_shift(button) for button in self._scene_launch_buttons_raw ]], name="Shifted_Scene_Buttons")

    def _create_session(self):
        self._session = SessionComponent(NUM_TRACKS, NUM_SCENES, auto_name=True, is_enabled=False, enable_skinning=True, layer=Layer(track_bank_left_button=self._left_button, track_bank_right_button=self._right_button, scene_bank_up_button=self._up_button, scene_bank_down_button=self._down_button, stop_track_clip_buttons=self._stop_buttons, stop_all_clips_button=self._stop_all_button, scene_launch_buttons=self._scene_launch_buttons, clip_launch_buttons=self._session_matrix, slot_launch_button=self._selected_slot_launch_button, selected_scene_launch_button=self._selected_scene_launch_button))
        self._session_zoom = SessionZoomingComponent(self._session, name='Session_Overview', enable_skinning=True, is_enabled=False, layer=Layer(button_matrix=self._shifted_matrix, nav_left_button=self._with_shift(self._left_button), nav_right_button=self._with_shift(self._right_button), nav_up_button=self._with_shift(self._up_button), nav_down_button=self._with_shift(self._down_button), scene_bank_buttons=self._shifted_scene_buttons))

    def _init_track_modes(self):
        self._track_modes = ModesComponent(name='Track_Modes', is_enabled=False)
        self._track_modes.default_behaviour = ImmediateBehaviour()
        self._track_modes.add_mode('pan', [AddLayerMode(self._mixer, Layer(pan_controls=self._mixer_encoders))])
        self._track_modes.add_mode('send_a', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 0)])
        self._track_modes.add_mode('send_b', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 1)])
        self._track_modes.add_mode('send_c', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 2)])
        self._track_modes.layer = Layer(pan_button=self._pan_button, send_a_button=self._send_a_button, send_b_button=self._send_b_button, send_c_button=self._send_c_button)
        self._track_modes.selected_mode = 'pan'

    def _create_mixer(self):
        self._mixer = MixerComponent(NUM_TRACKS, auto_name=True, is_enabled=False, invert_mute_feedback=True, layer=Layer(volume_controls=self._volume_controls, arm_buttons=self._arm_buttons, solo_buttons=self._solo_buttons, mute_buttons=self._mute_buttons, shift_button=self._shift_button, track_select_buttons=self._select_buttons, prehear_volume_control=self._prehear_control, crossfader_control=self._crossfader_control))
        self._mixer.master_strip().layer = Layer(volume_control=self._master_volume_control, select_button=self._master_select_button)

    def _create_transport(self):
        self._transport = TransportComponent(name='Transport', is_enabled=False, layer=Layer(shift_button=self._shift_button, play_button=self._play_button, stop_button=self._stop_button, record_button=self._record_button, metronome_button=self._metronome_button, tap_tempo_button=self._tap_tempo_button, nudge_down_button=self._nudge_down_button, nudge_up_button=self._nudge_up_button, quant_toggle_button=self._rec_quantization_button, overdub_button=self._overdub_button), play_toggle_model_transform=lambda v: v)

    def _create_device(self):
        self._device = DeviceComponent(name='Device', is_enabled=False, layer=Layer(parameter_controls=self._device_controls, bank_buttons=self._device_bank_buttons, on_off_button=self._device_on_off_button), device_selection_follows_track_selection=True)

    def _create_view_control(self):
        self._view_control = DetailViewCntrlComponent(name='View_Control', is_enabled=False, layer=Layer(device_nav_left_button=self._detail_left_button, device_nav_right_button=self._detail_right_button, device_clip_toggle_button=self._device_clip_toggle_button, detail_toggle_button=self._detail_toggle_button))
        self._view_control.device_clip_toggle_button.pressed_color = 'DefaultButton.On'

    def _create_quantization_selection(self):
        self._quantization_selection = QuantizationComponent(name='Quantization_Selection', is_enabled=False, layer=Layer(quantization_buttons=self._quantization_buttons))

    def _create_m4l_interface(self):
        self._m4l_interface = M4LInterfaceComponent(controls=self.controls, component_guard=self.component_guard, priority=1)
        self.get_control_names = self._m4l_interface.get_control_names
        self.get_control = self._m4l_interface.get_control
        self.grab_control = self._m4l_interface.grab_control
        self.release_control = self._m4l_interface.release_control

    def get_matrix_button(self, column, row):
        return self._matrix_rows_raw[row][column]

    def _product_model_id_byte(self):
        return 115