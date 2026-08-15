### Packet diagrams (VIEWMD-0049)

A `packet-beta`/`packet` block draws a fixed-width bit/byte field layout -- the kind used to
document a network protocol header -- wrapped onto rows of 32 bits each. See
[docs/mermaid-packet.md](mermaid-packet.md) for fixtures with the `+<count>` shorthand and a
field spanning a row boundary.

```mermaid
packet-beta
    title TCP Packet
    0-15: "Source Port"
    16-31: "Destination Port"
    32-63: "Sequence Number"
    64-95: "Acknowledgment Number"
    96-99: "Data Offset"
    100-105: "Reserved"
    106: "URG"
    107: "ACK"
    108: "PSH"
    109: "RST"
    110: "SYN"
    111: "FIN"
    112-127: "Window"
    128-143: "Checksum"
    144-159: "Urgent Pointer"
    160-191: "(Options and Padding)"
    192-255: "Data (variable length)"
```
