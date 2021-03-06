import wpilib
import wpilib.drive
from enum import Enum, auto
import math
import marsutils.math
import navx
from magicbot import will_reset_to

from common.encoder import BaseEncoder


class DriveMode(Enum):
    MECANUM = auto()
    TANK = auto()

    def toggle(self):
        if self == self.MECANUM:
            return self.TANK
        else:
            return self.MECANUM


class Drive:
    """
        Kevin has a high power drive train that uses
        mecanum and tank (Octocanum) to provide
        maneuverability and power
    """

    tank_drive: wpilib.drive.DifferentialDrive
    mecanum_drive: wpilib.drive.MecanumDrive

    octacanum_shifter_front: wpilib.DoubleSolenoid
    octacanum_shifter_rear: wpilib.DoubleSolenoid

    navx: navx.AHRS

    fl_drive_encoder: BaseEncoder
    fr_drive_encoder: BaseEncoder
    rl_drive_encoder: BaseEncoder
    rr_drive_encoder: BaseEncoder

    def __init__(self):
        # Current drive mode, this changes when a control calls its drive function
        self.drive_mode = will_reset_to(DriveMode.TANK)

        # Rotation, negative turns to the left, also known as z
        # Used for both
        self.rotation = will_reset_to(0)
        # Speed, positive is forward (joystick must be inverted)
        # Used for both
        self.y = will_reset_to(0)
        # Horizontal speed
        # Mecanum only
        self.x = will_reset_to(0)

        self.fod = will_reset_to(False)
        self.adjusted = will_reset_to(True)

    def drive_mecanum(self, y, x, z, fod=False, adjusted=True):
        self.rotation = z
        self.y = y
        self.x = x

        self.fod = fod
        self.adjusted = adjusted

        self.drive_mode = DriveMode.MECANUM

    def drive_tank(self, y, z, adjusted=True):
        self.rotation = z
        self.y = y

        self.adjusted = adjusted

        self.drive_mode = DriveMode.TANK

    def set_mode(self, mode: DriveMode):
        self.drive_mode = mode

    def zero_fod(self):
        """
        Zero the field oriented drive,

        makes the current facing direction "forward"
        """
        self.navx.zeroYaw()

    def execute(self):
        if self.adjusted:
            rot = marsutils.math.signed_square(self.rotation * 0.85)
            # cube the inputs because the drive train is incredibly touchy even at small inputs
            y = math.pow(self.y, 3)
            x = math.pow(self.x, 3)
        else:
            rot = self.rotation
            y = self.y
            x = self.x
        # feed the other drive train to appease the motor safety
        if self.drive_mode == DriveMode.TANK:
            self.octacanum_shifter_front.set(wpilib.DoubleSolenoid.Value.kForward)
            self.octacanum_shifter_rear.set(wpilib.DoubleSolenoid.Value.kForward)
            # We cube the inputs above
            self.tank_drive.arcadeDrive(y, rot, squareInputs=False)
            self.mecanum_drive.feed()
        elif self.drive_mode == DriveMode.MECANUM:
            self.octacanum_shifter_front.set(wpilib.DoubleSolenoid.Value.kReverse)
            self.octacanum_shifter_rear.set(wpilib.DoubleSolenoid.Value.kReverse)
            if self.fod:
                self.mecanum_drive.driveCartesian(
                    y, x, rot, gyroAngle=self.navx.getAngle()
                )
            else:
                self.mecanum_drive.driveCartesian(y, x, rot)
            self.tank_drive.feed()

    def reset_encoders(self):
        """ Reset all drive encoders
        """
        self.fl_drive_encoder.zero()
        self.fr_drive_encoder.zero()
        self.rl_drive_encoder.zero()
        self.rr_drive_encoder.zero()
