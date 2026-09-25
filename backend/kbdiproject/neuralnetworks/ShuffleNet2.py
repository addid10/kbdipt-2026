"""ShuffleNetV2 implementation used by the vegetation classifier checkpoint."""

import torch as torch
import torch.nn as nn


def channel_shuffle(x, groups=2):
    batch_size, channels, width, height = x.shape
    channels_per_group = channels // groups
    x = x.view(batch_size, groups, channels_per_group, width, height)
    x = torch.transpose(x, 1, 2).contiguous()
    return x.view(batch_size, -1, width, height)


def conv_1x1_bn(in_channels, out_channels, stride=1):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 1, stride, 0, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(True),
    )


class ShuffleBlock(nn.Module):
    def __init__(self, in_channels, out_channels, downsample=False):
        super().__init__()
        self.downsample = downsample
        half_channels = out_channels // 2

        if downsample:
            self.branch1 = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    in_channels,
                    3,
                    2,
                    1,
                    groups=in_channels,
                    bias=False,
                ),
                nn.BatchNorm2d(in_channels),
                nn.Conv2d(in_channels, half_channels, 1, 1, 0, bias=False),
                nn.BatchNorm2d(half_channels),
                nn.ReLU(True),
            )
            self.branch2 = nn.Sequential(
                nn.Conv2d(in_channels, half_channels, 1, 1, 0, bias=False),
                nn.BatchNorm2d(half_channels),
                nn.ReLU(True),
                nn.Conv2d(
                    half_channels,
                    half_channels,
                    3,
                    2,
                    1,
                    groups=half_channels,
                    bias=False,
                ),
                nn.BatchNorm2d(half_channels),
                nn.Conv2d(half_channels, half_channels, 1, 1, 0, bias=False),
                nn.BatchNorm2d(half_channels),
                nn.ReLU(True),
            )
        else:
            if in_channels != out_channels:
                raise ValueError("Non-downsampling ShuffleBlock requires equal channel counts.")
            self.branch2 = nn.Sequential(
                nn.Conv2d(half_channels, half_channels, 1, 1, 0, bias=False),
                nn.BatchNorm2d(half_channels),
                nn.ReLU(True),
                nn.Conv2d(
                    half_channels,
                    half_channels,
                    3,
                    1,
                    1,
                    groups=half_channels,
                    bias=False,
                ),
                nn.BatchNorm2d(half_channels),
                nn.Conv2d(half_channels, half_channels, 1, 1, 0, bias=False),
                nn.BatchNorm2d(half_channels),
                nn.ReLU(True),
            )

    def forward(self, x):
        if self.downsample:
            out = torch.cat((self.branch1(x), self.branch2(x)), 1)
        else:
            channels = x.shape[1]
            split = channels // 2
            x1 = x[:, :split, :, :]
            x2 = x[:, split:, :, :]
            out = torch.cat((x1, self.branch2(x2)), 1)
        return channel_shuffle(out, 2)


class ShuffleNet2(nn.Module):
    def __init__(self, num_classes=2, input_size=224, net_type=1):
        super().__init__()
        if input_size % 32 != 0:
            raise ValueError("input_size must be divisible by 32.")

        self.stage_repeat_num = [4, 8, 4]
        channel_map = {
            0.5: [3, 24, 48, 96, 192, 1024],
            1: [3, 24, 116, 232, 464, 1024],
            1.5: [3, 24, 176, 352, 704, 1024],
            2: [3, 24, 244, 488, 976, 2948],
        }
        if net_type not in channel_map:
            raise ValueError("net_type must be one of 0.5, 1, 1.5, or 2.")
        self.out_channels = channel_map[net_type]

        self.conv1 = nn.Conv2d(3, self.out_channels[1], 3, 2, 1)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        stages = []
        in_channels = self.out_channels[1]
        for stage_index, repeat_count in enumerate(self.stage_repeat_num):
            out_channels = self.out_channels[2 + stage_index]
            for block_index in range(repeat_count):
                if block_index == 0:
                    stages.append(ShuffleBlock(in_channels, out_channels, downsample=True))
                else:
                    stages.append(ShuffleBlock(in_channels, in_channels, downsample=False))
                in_channels = out_channels
        self.stages = nn.Sequential(*stages)

        self.conv5 = conv_1x1_bn(self.out_channels[-2], self.out_channels[-1], 1)
        self.g_avg_pool = nn.AvgPool2d(kernel_size=int(input_size / 32))
        self.fc = nn.Linear(self.out_channels[-1], num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.maxpool(x)
        x = self.stages(x)
        x = self.conv5(x)
        x = self.g_avg_pool(x)
        x = x.view(-1, self.out_channels[-1])
        return self.fc(x)
